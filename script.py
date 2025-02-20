from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import yfinance as yf
from datetime import datetime

app = Flask(__name__)
CORS(app)

def get_wikidata_id(company_name):
    url = f"https://www.wikidata.org/w/api.php?action=wbsearchentities&search={company_name}&language=en&format=json"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if "search" in data and data["search"]:
            return data["search"][0]["id"]
        return None
    except requests.exceptions.RequestException:
        return None

def get_wikidata_details(wikidata_id):
    query = f"""
    SELECT ?industryLabel ?countryLabel ?hqLabel ?founded ?employees WHERE {{
        OPTIONAL {{ wd:{wikidata_id} wdt:P452 ?industry. }}
        OPTIONAL {{ wd:{wikidata_id} wdt:P17 ?country. }}
        OPTIONAL {{ wd:{wikidata_id} wdt:P159 ?hq. }}
        OPTIONAL {{ wd:{wikidata_id} wdt:P571 ?founded. }}
        OPTIONAL {{ wd:{wikidata_id} wdt:P1128 ?employees. }}
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }} LIMIT 1
    """
    
    results = fetch_wikidata(query)
    if not results:
        return {}
    
    result = results[0]
    return {
        "Industry": result.get("industryLabel", {}).get("value", "N/A"),
        "Country": result.get("countryLabel", {}).get("value", "N/A"),
        "Headquarters": result.get("hqLabel", {}).get("value", "N/A"),
        "Founded": result.get("founded", {}).get("value", "N/A"),
        "Employees": result.get("employees", {}).get("value", "N/A")
    }

def get_funding_rounds(wikidata_id):
    query = f"""
    SELECT ?investmentLabel ?amount ?currencyLabel WHERE {{
      ?investment wdt:P3320 wd:{wikidata_id}.
      OPTIONAL {{ ?investment wdt:P4999 ?amount. }}
      OPTIONAL {{ ?investment wdt:P38 ?currency. }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    """

    results = fetch_wikidata(query)
    funding_data = []

    for result in results:
        amount = result.get("amount", {}).get("value", "Unknown")
        currency = result.get("currencyLabel", {}).get("value", "Unknown")
        funding_data.append({
            "round": result.get('investmentLabel', {}).get('value', 'Unknown'),
            "amount": amount,
            "currency": currency
        })

    return funding_data if funding_data else []

def fetch_wikidata(query):
    endpoint = "https://query.wikidata.org/sparql"
    params = {"query": query, "format": "json"}

    try:
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        data = response.json()
        return data["results"]["bindings"] if "results" in data else []
    except requests.exceptions.RequestException:
        return []

def get_ticker_from_name(company_name):
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={company_name}"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("quotes", [{}])[0].get("symbol") if data.get("quotes") else None
    except requests.exceptions.RequestException:
        return None

def get_company_financials(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Basic company information
        company_info = {
            "Company Name": info.get("longName", "N/A"),
            "Sector": info.get("sector", "N/A"),
            "Industry": info.get("industry", "N/A"),
            "Country": info.get("country", "N/A"),
            "Website": info.get("website", "N/A"),
            "Description": info.get("longBusinessSummary", "N/A"),
            "Full Time Employees": info.get("fullTimeEmployees", "N/A")
        }

        # Market data
        market_data = {
            "Market Cap": info.get("marketCap", "N/A"),
            "Current Price": info.get("currentPrice", "N/A"),
            "52 Week High": info.get("fiftyTwoWeekHigh", "N/A"),
            "52 Week Low": info.get("fiftyTwoWeekLow", "N/A"),
            "50 Day Average": info.get("fiftyDayAverage", "N/A"),
            "200 Day Average": info.get("twoHundredDayAverage", "N/A"),
            "Volume": info.get("volume", "N/A"),
            "Average Volume": info.get("averageVolume", "N/A")
        }

        # Financial metrics
        financial_metrics = {
            "PE Ratio": info.get("trailingPE", "N/A"),
            "Forward PE": info.get("forwardPE", "N/A"),
            "EPS": info.get("trailingEps", "N/A"),
            "Forward EPS": info.get("forwardEps", "N/A"),
            "PEG Ratio": info.get("pegRatio", "N/A"),
            "Price to Book": info.get("priceToBook", "N/A"),
            "Price to Sales": info.get("priceToSalesTrailing12Months", "N/A"),
            "Beta": info.get("beta", "N/A")
        }

        # Income statement metrics
        income_statement = {
            "Revenue": info.get("totalRevenue", "N/A"),
            "Revenue Growth": info.get("revenueGrowth", "N/A"),
            "Gross Profits": info.get("grossProfits", "N/A"),
            "EBITDA": info.get("ebitda", "N/A"),
            "Net Income": info.get("netIncomeToCommon", "N/A"),
            "Profit Margin": info.get("profitMargins", "N/A"),
            "Operating Margin": info.get("operatingMargins", "N/A"),
            "Gross Margin": info.get("grossMargins", "N/A")
        }

        # Balance sheet metrics
        balance_sheet = {
            "Total Cash": info.get("totalCash", "N/A"),
            "Total Debt": info.get("totalDebt", "N/A"),
            "Current Ratio": info.get("currentRatio", "N/A"),
            "Quick Ratio": info.get("quickRatio", "N/A"),
            "Total Assets": info.get("totalAssets", "N/A"),
            "Total Liabilities": info.get("totalDebt", "N/A"),
            "Book Value": info.get("bookValue", "N/A")
        }

        # Dividend information
        dividend_info = {
            "Dividend Rate": info.get("dividendRate", "N/A"),
            "Dividend Yield": info.get("dividendYield", "N/A"),
            "Payout Ratio": info.get("payoutRatio", "N/A"),
            "Ex-Dividend Date": info.get("exDividendDate", "N/A")
        }

        return {
            "company_info": company_info,
            "market_data": market_data,
            "financial_metrics": financial_metrics,
            "income_statement": income_statement,
            "balance_sheet": balance_sheet,
            "dividend_info": dividend_info
        }
    except Exception as e:
        print(f"Error fetching financial data: {e}")
        return None

def get_competitors(company_name, wikidata_id=None, ticker=None, industry=None):
    competitors = []
    
    # Method 1: Yahoo Finance (no country filter now)
    if ticker:
        try:
            stock = yf.Ticker(ticker)
            all_competitors = stock.info.get('competitors', [])
            competitors = [c for c in all_competitors if c != company_name]
        except Exception:
            pass

    if not competitors:
        industry_id = None
        if industry:
            industry_id = search_industry_id(industry)
        competitors = get_industry_competitors(
            company_id=wikidata_id,
            industry_id=industry_id,
            industry_name=industry
        )

    if not competitors and wikidata_id:
        competitors = get_direct_competitors(wikidata_id)
    
    return competitors or ["No competitors found"]

def get_industry_competitors(company_id=None, industry_id=None, industry_name=None):
    if not industry_id:
        if company_id:
            industry_id = get_industry_id(company_id)
        elif industry_name:
            industry_id = search_industry_id(industry_name)
    
    if not industry_id:
        return []

    query = f"""
    SELECT DISTINCT ?company ?companyLabel WHERE {{
        ?company wdt:P452 wd:{industry_id}.
        {f"FILTER (?company != wd:{company_id})" if company_id else ""}
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    ORDER BY DESC(?company)
    """
    
    results = fetch_wikidata(query)
    return [result['companyLabel']['value'] for result in results]

def get_direct_competitors(wikidata_id):
    query = f"""
    SELECT ?competitorLabel WHERE {{
        wd:{wikidata_id} wdt:P4886 ?competitor.
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    """
    results = fetch_wikidata(query)
    return [result['competitorLabel']['value'] for result in results]

def get_industry_id(wikidata_id):
    query = f"""
    SELECT ?industry WHERE {{
        wd:{wikidata_id} wdt:P452 ?industry.
    }}
    """
    results = fetch_wikidata(query)
    return results[0]['industry']['value'].split('/')[-1] if results else None

def search_industry_id(industry_name):
    query = f"""
    SELECT ?industry WHERE {{
        ?industry rdfs:label "{industry_name}"@en;
                  wdt:P31/wdt:P279* wd:Q8148.
    }}
    LIMIT 1
    """
    results = fetch_wikidata(query)
    return results[0]['industry']['value'].split('/')[-1] if results else None

@app.route('/api/company_analysis', methods=['POST'])
def company_analysis():
    try:
        data = request.get_json()
        
        if not data or 'company_name' not in data:
            return jsonify({
                'error': 'Missing company_name in request body'
            }), 400
            
        company_name = data['company_name'].strip()
        
        # Get Wikidata information
        wikidata_id = get_wikidata_id(company_name)
        response_data = {
            'company_name': company_name,
            'wikidata_id': wikidata_id,
            'timestamp': datetime.now().isoformat()
        }
        
        # Get company details from Wikidata
        if wikidata_id:
            response_data['wikidata_details'] = get_wikidata_details(wikidata_id)
            response_data['funding_rounds'] = get_funding_rounds(wikidata_id)
        
        # Get Yahoo Finance information
        ticker = get_ticker_from_name(company_name)
        response_data['ticker'] = ticker
        
        if ticker:
            response_data['financial_data'] = get_company_financials(ticker)
        
        # Get competitors (all companies; no country filtering)
        response_data['competitors'] = get_competitors(
            company_name=company_name,
            wikidata_id=wikidata_id,
            ticker=ticker,
            industry=response_data.get('wikidata_details', {}).get('Industry')
        )
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            'error': f'An error occurred: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
