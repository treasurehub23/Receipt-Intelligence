
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, extract
from sqlalchemy.orm import Session
 
from db.database import get_db
from db.models import Expense
from schemas import AnalyticsSummary, CategoryBreakdown, MonthBreakdown
 
router = APIRouter()