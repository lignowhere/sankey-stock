"""
Flask application for Financial Sankey Diagram Generator
Integrates vnstock for Vietnamese stock market data
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import traceback
import os

# Import our modules
from data_fetcher import fetch_balance_sheet, fetch_income_statement, fetch_cash_flow
import balance
import cashflow
import income

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')


@app.route('/api/generate-sankey', methods=['POST'])
def generate_sankey():
    """
    Generate Sankey diagram data from vnstock
    
    Expected JSON payload:
    {
        "symbol": "VNM",
        "report_type": "balance",  // or "income", "cashflow"
        "period": "Q1",  // or "Q2", "Q3", "Q4", "year"
        "year": 2024
    }
    
    Returns:
    {
        "success": true,
        "data": "Source [Value] Target\n...",
        "symbol": "VNM",
        "report_type": "balance",
        "period": "Q1",
        "year": 2024
    }
    """
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        symbol = data.get('symbol', '').strip().upper()
        report_type = data.get('report_type', '').strip().lower()
        period = data.get('period', '').strip()
        year = data.get('year')
        
        # Validate inputs
        if not symbol:
            return jsonify({
                'success': False,
                'error': 'Stock symbol is required'
            }), 400
        
        if report_type not in ['balance', 'income', 'cashflow']:
            return jsonify({
                'success': False,
                'error': 'Invalid report type. Must be: balance, income, or cashflow'
            }), 400
        
        if not period:
            return jsonify({
                'success': False,
                'error': 'Period is required'
            }), 400
        
        try:
            year = int(year)
            if year < 2000 or year > 2030:
                raise ValueError("Year out of range")
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'Invalid year. Must be between 2000 and 2030'
            }), 400
        
        # Fetch data from vnstock
        if report_type == 'balance':
            df = fetch_balance_sheet(symbol, period, year)
            sankey_data = balance.extract_flows_from_dataframe(df)
        elif report_type == 'income':
            df = fetch_income_statement(symbol, period, year)
            sankey_data = income.extract_flows_from_dataframe(df)
        elif report_type == 'cashflow':
            df = fetch_cash_flow(symbol, period, year)
            sankey_data = cashflow.extract_flows_from_dataframe(df)
        else:
            return jsonify({
                'success': False,
                'error': 'Unknown report type'
            }), 400
        
        # Check if we got valid data
        if not sankey_data or sankey_data.startswith('// Error'):
            return jsonify({
                'success': False,
                'error': sankey_data or 'Failed to generate Sankey data'
            }), 500
        
        # Return success response
        return jsonify({
            'success': True,
            'data': sankey_data,
            'symbol': symbol,
            'report_type': report_type,
            'period': period,
            'year': year
        })
        
    except Exception as e:
        # Log the full error for debugging
        print(f"Error generating Sankey diagram: {str(e)}")
        print(traceback.format_exc())
        
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


@app.route('/api/generate-all-reports', methods=['POST'])
def generate_all_reports():
    """
    Generate all 3 Sankey diagrams data from vnstock
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        symbol = data.get('symbol', '').strip().upper()
        period = data.get('period', '').strip()
        year = data.get('year')
        
        if not symbol or not period or not year:
            return jsonify({'success': False, 'error': 'Missing required parameters'}), 400

        results = {}
        
        # 1. Balance Sheet
        try:
            df_balance = fetch_balance_sheet(symbol, period, year)
            results['balance'] = balance.extract_flows_from_dataframe(df_balance)
        except Exception as e:
            results['balance'] = f"// Error: {str(e)}"

        # 2. Income Statement
        try:
            df_income = fetch_income_statement(symbol, period, year)
            results['income'] = income.extract_flows_from_dataframe(df_income)
        except Exception as e:
            results['income'] = f"// Error: {str(e)}"

        # 3. Cash Flow
        try:
            df_cashflow = fetch_cash_flow(symbol, period, year)
            results['cashflow'] = cashflow.extract_flows_from_dataframe(df_cashflow)
        except Exception as e:
            results['cashflow'] = f"// Error: {str(e)}"
            
        return jsonify({
            'success': True,
            'data': results,
            'symbol': symbol,
            'period': period,
            'year': year
        })
        
    except Exception as e:
        print(f"Error generating all reports: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Financial Sankey Diagram Generator'
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting Financial Sankey Diagram Generator on port {port}...")
    app.run(debug=True, host='0.0.0.0', port=port)
