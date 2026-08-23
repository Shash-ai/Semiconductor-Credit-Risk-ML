"""Project paths and modelling assumptions for Semicon 2.0 credit-risk work."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "01_Raw_Data"
CLEAN = ROOT / "02_Clean_Data"
NOTEBOOKS = ROOT / "03_Notebooks"
WEB_RAW = RAW / "Web_Scraped"
MASTER_DIR = CLEAN / "Master"
EDA_DIR = CLEAN / "EDA"

for d in (WEB_RAW, MASTER_DIR, EDA_DIR, CLEAN / "Macro", CLEAN / "Banking", CLEAN / "Industry", CLEAN / "Company_Financials"):
    d.mkdir(parents=True, exist_ok=True)

AS_OF_YEAR = 2026
PANEL_YEARS = list(range(2019, AS_OF_YEAR + 1))

# Conservative project-finance leverage used only as a PUBLIC PROXY for bank
# exposure. Loan-level bank books are not disclosed. Documented in the master
# data dictionary.
ASSUMED_DEBT_SHARE = 0.70
ASSUMED_TENOR_YEARS = 10

LISTED_TICKERS = {
    "CG Power and Industrial Solutions Limited": "CGPOWER.NS",
    "Kaynes Technology India Limited": "KAYNES.NS",
    "Micron Technology Inc.": "MU",
    "Vama Sundari Investments (Delhi) Private Limited / Foxconn": "2317.TW",
}

WORLD_BANK_INDICATORS = {
    "gdp_growth": "NY.GDP.MKTP.KD.ZG",
    "cpi_inflation": "FP.CPI.TOTL.ZG",
    "inr_usd": "PA.NUS.FCRF",
    "domestic_credit_gdp": "FS.AST.DOMS.GD.ZS",
    "manufacturing_va_growth": "NV.IND.MANF.KD.ZG",
    "high_tech_exports_share": "TX.VAL.TECH.MF.ZS",
}

# HS chapters for semiconductors / electronic ICs (UN Comtrade)
COMTRADE_HS = ["8541", "8542"]
