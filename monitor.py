"""Executar periodicamente com cron ou Agendador de Tarefas."""
from datetime import date, timedelta
import os
from dotenv import load_dotenv
from radar import search, save_results, email_alert

load_dotenv()
if __name__ == '__main__':
    if not os.getenv('SERPAPI_KEY'):
        raise SystemExit('Configure SERPAPI_KEY. O monitor não envia alertas fictícios.')
    budget = float(os.getenv('BUDGET', '2500'))
    start = date.today() + timedelta(days=30)
    offers, errors = search(start.isoformat(), 4, int(os.getenv('ADULTS','2')), int(os.getenv('CHILDREN','0')), ['GRU','CGH','VCP'], ['Navegantes','Penha','Itajaí','Balneário Camboriú'])
    save_results(offers[:100])
    for item in offers:
        if item['total'] <= budget:
            try:
                print(email_alert(item, budget))
            except Exception as exc:
                print('Erro ao enviar alerta:', exc)
    for error in errors:
        print('Aviso:', error)
