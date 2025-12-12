CRYPTO PORTFOLIO TRACKER
By YAGANTI SREEVARDHAN REDDY

(Project Duration: October 15,2025 – DECEMBER 15,2025)

About This Project:

Crypto Portfolio Tracker is a full-stack Flask web application that allows users to:

Track and manage their cryptocurrency investments

Maintain crypto portfolios and wallets

View live market data from CoinGeckoAPI

Generate profit/loss analytics

Get smart crypto recommendations based on 24hr 

Perform encryption/decryption using a built-in Cipher tool and hashing

This project demonstrates backend development, API handling, data processing, authentication, visualization, and UI/UX design.

 Project Modules:
	Module Name	Description	of	Files:

1	Authentication System	User Registration, Login, Session Management	Flask, SQLAlchemy	auth.py

2	Crypto Dashboard	Live prices, charts, search, sparkline graphs	CoinGecko API, Matplotlib	dashboard.py

3	Portfolio Manager	Track holdings, P/L analytics, pie & bar charts	Flask, SQLAlchemy	portfolio.py

4	Wallet Manager	wallet support, live valuation	CoinGecko API	wallet.py

5	Recommendation Engine	Suggests coins based on 24h performance	Python, Matplotlib	recommend.py

6	Cipher Tool	Caesar Encryption, Decryption, SHA-256 hashing	Python, Hashlib	cipher.py

7	Database Models	User, PortfolioItem, WalletItem models	SQLAlchemy	models.py

8	Frontend UI	Complete Dark-Mode Neon Web UI	HTML, CSS	static/ & templates/

 Key Features:
 Secure Authentication:

User login, logout, and session handling
Password hashing (Werkzeug)

 Real-time Crypto Dashboard:

Market listings with sparkline charts

Search functionality

 Portfolio Tracking:

Add/update/remove coins

Auto-fetch live INR prices

Profit/Loss % calculation

Dynamic pie chart & bar chart visualizations

 Wallet System:

Manage holdings easily

Auto valuation

 Recommendation System:

Picks coins with positive price trends

Ranks by market cap & volume

Sparkline micro-charts included

 Cipher Encryption Tool:

Caesar encryption & decryption

SHA-256 hashing support

 Technologies Used:
Backend:

Flask • Python • SQLAlchemy • Flask-Login • Matplotlib • PyCoinGecko

Frontend:

HTML • CSS • JavaScript • Neon Dark Theme

Database:
SQLite (default) — easily extendable to PostgreSQL/MySQL
