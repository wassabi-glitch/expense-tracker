import sys
import os

from app.session import SessionLocal
from app.models import EntityLedger, FinancialEvent

def inspect():
    db = SessionLocal()
    ledgers = db.query(EntityLedger).filter(EntityLedger.subcategory_id == 7).all()
    print(f"Found {len(ledgers)} ledgers for subcategory 7")
    for ledger in ledgers:
        print(f"Ledger {ledger.id}: event_id={ledger.event_id}")
        if ledger.event_id:
            event = db.query(FinancialEvent).filter(FinancialEvent.id == ledger.event_id).first()
            print(f"  -> Event {event.id}: type={event.event_type}, status={event.status}, owner_id={event.owner_id}")

inspect()
