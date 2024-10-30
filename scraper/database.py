from datetime import date
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Column, BigInteger, Text, Date, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError
import logging
from config import DATABASE_URL

logger = logging.getLogger(__name__)

engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)
SessionFactory = sessionmaker(bind=engine)
Session = scoped_session(SessionFactory)
Base = declarative_base()

class Mugshot(Base):
    __tablename__ = 'mugshots'

    id = Column(BigInteger, primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    firstName = Column(Text, server_default='')
    lastName = Column(Text, server_default='')
    dateOfBooking = Column(Date)
    stateOfBooking = Column(Text)
    countyOfBooking = Column(Text)
    offenseDescription = Column(Text)
    additionalDetails = Column(Text)
    imagePath = Column(Text)
    fb_status = Column(Text)

class DatabaseManager:
    @staticmethod
    def create_table_if_not_exists():
        Base.metadata.create_all(engine)
        logger.info("Mugshots table created or already exists")

    @staticmethod
    def get_db_session():
        return Session()

    @staticmethod
    def insert_mugshot(mugshot_data):
        session = Session()
        try:
            new_mugshot = Mugshot(**mugshot_data)
            session.add(new_mugshot)
            session.commit()
            logger.info(f"Successfully added new mugshot: {mugshot_data['firstName']} {mugshot_data['lastName']}")
        except SQLAlchemyError as e:
            logger.error(f"Failed to insert mugshot into database: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def is_in_database(firstName, lastName, dateOfBooking):
        session = Session()
        try:
            result = session.query(Mugshot).filter(
                Mugshot.firstName == firstName,
                Mugshot.lastName == lastName,
                Mugshot.dateOfBooking == dateOfBooking
            ).first()
            return result is not None
        except SQLAlchemyError as e:
            logger.error(f"Error checking database for mugshot: {e}")
            return False
        finally:
            session.close()

    @staticmethod
    def cleanup():
        Session.remove()
        
    @staticmethod
    def get_existing_mugshots(state, county):
        with DatabaseManager.get_db_session() as session:
            result = session.query(
                Mugshot.firstName,
                Mugshot.lastName,
                Mugshot.dateOfBooking
            ).filter(
                Mugshot.stateOfBooking == state,
                Mugshot.countyOfBooking == county
            ).all()
            return [{"firstName": r.firstName, "lastName": r.lastName, "dateOfBooking": r.dateOfBooking} for r in result]

    @staticmethod
    def get_unprocessed_mugshots():
        with DatabaseManager.get_db_session() as session:
            return session.query(Mugshot).filter(Mugshot.fb_status == "pending").all()

    @staticmethod
    def mark_as_processed(mugshot_id):
        with DatabaseManager.get_db_session() as session:
            mugshot = session.query(Mugshot).filter(Mugshot.id == mugshot_id).first()
            if mugshot:
                mugshot.fb_status = "posted"
                session.commit()
                logger.info(f"Marked mugshot as processed: {mugshot_id}")
            else:
                logger.warning(f"Mugshot not found: {mugshot_id}")

    @staticmethod
    def parse_content(html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract additional details
        additional_details = ""
        dl_tag = soup.find('dl')
        if dl_tag:
            for dt, dd in zip(dl_tag.find_all('dt'), dl_tag.find_all('dd')):
                additional_details += f"{dt.text.strip()}: {dd.text.strip()}\n"
        
        # Extract offense description
        offense_description = ""
        charges_section = soup.find(['h2', 'h3', 'h4'], text=lambda t: 'charges' in t.lower() if t else False)
        
        if charges_section:
            next_element = charges_section.find_next()
            while next_element and next_element.name not in ['h2', 'h3', 'h4']:
                if next_element.name == 'p':
                    offense_description += next_element.text.strip() + "\n"
                elif next_element.name == 'ul':
                    for li in next_element.find_all('li'):
                        offense_description += f"- {li.text.strip()}\n"
                next_element = next_element.next_sibling
        
        if not offense_description:
            logger.warning("No offense description found. Checking for any content after additional details.")
            last_dd = soup.find_all('dd')[-1] if soup.find_all('dd') else None
            if last_dd:
                next_element = last_dd.find_next()
                while next_element:
                    if next_element.name in ['p', 'div']:
                        offense_description += next_element.text.strip() + "\n"
                    next_element = next_element.next_sibling

        logger.debug(f"Parsed Offense Description: {offense_description}")
        logger.debug(f"Parsed Additional Details: {additional_details}")
        
        return offense_description.strip(), additional_details.strip()
    
    @staticmethod
    def get_unprocessed_mugshots():
        session = Session()
        try:
            unprocessed_mugshots = session.query(Mugshot).filter_by(fb_status="pending").all()
            return unprocessed_mugshots
        except Exception as e:
            logger.error(f"Error getting unprocessed mugshots: {e}")
            return []
        finally:
            session.close()

    @staticmethod
    def mark_as_processed(mugshot_id):
        session = Session()
        try:
            mugshot = session.query(Mugshot).filter_by(id=mugshot_id).first()
            mugshot.fb_status = "posted"
            session.commit()
            logger.info(f"Marked mugshot as processed: {mugshot_id}")
        except Exception as e:
            logger.error(f"Error marking mugshot as processed: {e}")
            session.rollback()
        finally:
            session.close()

    @staticmethod
    def get_todays_unprocessed_mugshots(today: date):
        with Session() as session:
            mugshots = session.query(Mugshot).filter(
                Mugshot.dateOfBooking == today,
                Mugshot.fb_status == 'pending'
            ).all()
            return mugshots