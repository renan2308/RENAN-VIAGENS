"""Pesquisa e combinação de ofertas. Preços reais dependem da SerpApi."""
import os
import sqlite3
import smtplib
import hashlib
from datetime import date, timedelta
from email.message import EmailMessage
from pathlib import Path
import requests

DB = Path(os.getenv('RADAR_DB', 'radar.db'))
ORIGINS = ['GRU', 'CGH', 'VCP']
DESTINATIONS = ['Navegantes', 'Penha', 'Itajaí', 'Balneário Camboriú']


def db():
    conn = sqlite3.connect(DB)
    conn.execute('CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, checked_at TEXT DEFAULT CURRENT_TIMESTAMP, signature TEXT, departure TEXT, arrival TEXT, hotel TEXT, city TEXT, start TEXT, finish TEXT, total REAL, source TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS alerts (signature TEXT PRIMARY KEY, sent_at TEXT DEFAULT CURRENT_TIMESTAMP)')
    conn.commit()
    return conn


def get_json(params):
    key = os.getenv('SERPAPI_KEY', '').strip()
    if not key:
        raise RuntimeError('Configure SERPAPI_KEY no arquivo .env para pesquisar preços reais.')
    r = requests.get('https://serpapi.com/search.json', params={**params, 'api_key': key}, timeout=35)
    r.raise_for_status()
    data = r.json()
    if data.get('error'):
        raise RuntimeError(str(data['error']))
    return data


def flight_offers(start, finish, adults, children, origins):
    offers = []
    errors = []
    for origin in origins:
        try:
            data = get_json({'engine': 'google_flights', 'departure_id': origin, 'arrival_id': 'NVT', 'outbound_date': start, 'return_date': finish, 'type': 1, 'currency': 'BRL', 'hl': 'pt', 'gl': 'br', 'adults': adults, 'children': children})
            for item in (data.get('best_flights', []) + data.get('other_flights', [])):
                price = item.get('price')
                if isinstance(price, (int, float)) and price > 0:
                    offers.append({'origin': origin, 'price': float(price), 'airlines': ', '.join(sorted({x.get('airline', '') for x in item.get('flights', []) if x.get('airline')})), 'link': data.get('search_metadata', {}).get('google_flights_url', '')})
        except Exception as exc:
            errors.append(f'{origin}: {exc}')
    return sorted(offers, key=lambda x: x['price']), errors


def hotel_offers(city, start, finish, adults, children):
    try:
        data = get_json({'engine': 'google_hotels', 'q': f'hotéis em {city}, Santa Catarina, Brasil', 'check_in_date': start, 'check_out_date': finish, 'adults': adults, 'children': children, 'currency': 'BRL', 'gl': 'br', 'hl': 'pt'})
        offers = []
        for item in data.get('properties', []):
            rate = item.get('total_rate', {})
            amount = rate.get('extracted_lowest') if isinstance(rate, dict) else None
            if not isinstance(amount, (int, float)) or amount <= 0:
                continue
            offers.append({'hotel': item.get('name', 'Hospedagem'), 'city': city, 'price': float(amount), 'rating': item.get('overall_rating'), 'link': item.get('link', '')})
        return sorted(offers, key=lambda x: x['price']), []
    except Exception as exc:
        return [], [f'{city}: {exc}']


def demo_offers(start, finish, adults, children, origins, cities):
    """Dados fictícios fixos, exclusivamente para testar a interface."""
    flights = [{'origin': o, 'price': 480 + i*85, 'airlines': 'Companhia ilustrativa', 'link': ''} for i, o in enumerate(origins)]
    hotels = [{'hotel': f'Hospedagem exemplo — {c}', 'city': c, 'price': 720 + i*150, 'rating': None, 'link': ''} for i, c in enumerate(cities)]
    return flights, hotels


def combine(flights, hotels, start, finish, adults, children, demo=False):
    # Preço do Google Flights geralmente é exibido para o conjunto de passageiros selecionados.
    # Preço total do Google Hotels corresponde à estadia selecionada.
    result = []
    for f in flights[:8]:
        for h in hotels[:12]:
            total = f['price'] + h['price']
            signature = hashlib.sha256(f"{start}|{finish}|{f['origin']}|{h['hotel']}|{total}".encode()).hexdigest()
            result.append({**f, **h, 'start': start, 'finish': finish, 'total': total, 'signature': signature, 'demo': demo, 'travelers': adults+children})
    return sorted(result, key=lambda x: x['total'])


def search(start, nights, adults, children, origins, cities, demo=False):
    finish = (date.fromisoformat(start) + timedelta(days=nights)).isoformat()
    if demo:
        flights, hotels = demo_offers(start, finish, adults, children, origins, cities)
        return combine(flights, hotels, start, finish, adults, children, True), []
    flights, errors = flight_offers(start, finish, adults, children, origins)
    hotels = []
    for city in cities:
        found, err = hotel_offers(city, start, finish, adults, children)
        hotels.extend(found)
        errors.extend(err)
    return combine(flights, hotels, start, finish, adults, children), errors


def save_results(items):
    with db() as conn:
        conn.executemany('INSERT INTO history (signature, departure, arrival, hotel, city, start, finish, total, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', [(x['signature'], x['origin'], 'NVT', x['hotel'], x['city'], x['start'], x['finish'], x['total'], 'demo' if x['demo'] else 'serpapi') for x in items])


def email_alert(item, ceiling):
    required = ['SMTP_HOST', 'SMTP_USER', 'SMTP_PASSWORD', 'ALERT_TO']
    if any(not os.getenv(x) for x in required):
        return False, 'SMTP não configurado.'
    if item['demo'] or item['total'] > ceiling:
        return False, 'Não elegível para alerta.'
    with db() as conn:
        if conn.execute('SELECT 1 FROM alerts WHERE signature=?', (item['signature'],)).fetchone():
            return False, 'Alerta já enviado para esta oferta.'
        msg = EmailMessage()
        msg['Subject'] = f"Radar de Viagens: pacote estimado R$ {item['total']:.2f}"
        msg['From'] = os.getenv('SMTP_USER')
        msg['To'] = os.getenv('ALERT_TO')
        msg.set_content(f"{item['origin']} → NVT | {item['start']} a {item['finish']}\n{item['hotel']} ({item['city']})\nVoo: R$ {item['price']:.2f} | Hospedagem: R$ {item['total']-item['price']:.2f}\nTotal estimado: R$ {item['total']:.2f}\nVerifique disponibilidade, taxas, bagagem e traslados antes de reservar.\nVoo: {item.get('link','')}\nHospedagem: {item.get('link','')}")
        with smtplib.SMTP(os.getenv('SMTP_HOST'), int(os.getenv('SMTP_PORT', '587')), timeout=30) as smtp:
            smtp.starttls()
            smtp.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASSWORD'))
            smtp.send_message(msg)
        conn.execute('INSERT INTO alerts (signature) VALUES (?)', (item['signature'],))
    return True, 'E-mail enviado.'
