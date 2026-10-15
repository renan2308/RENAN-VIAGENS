from datetime import date, timedelta
import os
import streamlit as st
from dotenv import load_dotenv
from radar import ORIGINS, DESTINATIONS, search, save_results, db, email_alert

load_dotenv()
st.set_page_config(page_title='Radar de Viagens', page_icon='✈️', layout='wide')
st.title('✈️ Radar de Viagens')
st.caption('São Paulo → Navegantes | Voos + hospedagem | Comparação de pacotes')
mode = st.toggle('Modo demonstração (preços fictícios)', value=not bool(os.getenv('SERPAPI_KEY')))
if mode:
    st.warning('MODO DEMONSTRAÇÃO: todos os valores são fictícios, não são ofertas reais.')
else:
    st.info('Consulta real via SerpApi. Cada busca pode consumir várias consultas pagas. Os preços são estimativas sujeitas a mudança.')
with st.sidebar:
    st.header('Configuração da viagem')
    origins = st.multiselect('Aeroportos de saída', ORIGINS, default=ORIGINS)
    cities = st.multiselect('Onde se hospedar', DESTINATIONS, default=DESTINATIONS)
    adults = st.number_input('Adultos', 1, 8, 2)
    children = st.number_input('Crianças', 0, 8, 0)
    begin = st.date_input('Primeira data possível', date.today() + timedelta(days=30), min_value=date.today()+timedelta(days=1))
    end = st.date_input('Última data de partida', date.today() + timedelta(days=45), min_value=begin)
    nights = st.slider('Noites de hospedagem', 1, 14, (3, 5))
    budget = st.number_input('Alerta: pacote até R$', 100, 100000, 2500, step=100)
    st.caption('Datas flexíveis: pesquisa algumas combinações de partidas e duração. Para evitar custos, o limite é 12 combinações por execução.')
    run = st.button('🔎 Pesquisar pacotes', type='primary', use_container_width=True)

if run:
    if not origins or not cities:
        st.error('Selecione ao menos um aeroporto e uma cidade.')
    else:
        span = (end-begin).days
        steps = sorted(set([0, span//3, 2*span//3, span]))
        dates = [begin+timedelta(days=x) for x in steps]
        durations = sorted(set([nights[0], nights[1]]))
        tasks = [(d.isoformat(), n) for d in dates for n in durations][:12]
        results, errors = [], []
        bar = st.progress(0)
        for i, (d, n) in enumerate(tasks):
            offers, errs = search(d, n, adults, children, origins, cities, demo=mode)
            results.extend(offers)
            errors.extend(errs)
            bar.progress((i+1)/len(tasks))
        results.sort(key=lambda x: x['total'])
        st.session_state['results'] = results
        st.session_state['errors'] = errors
        if results:
            save_results(results[:100])

results = st.session_state.get('results', [])
errors = st.session_state.get('errors', [])
if errors:
    with st.expander(f'{len(errors)} avisos de consulta'):
        for err in sorted(set(errors)):
            st.write(err)
if results:
    best = results[0]
    a,b,c = st.columns(3)
    a.metric('Melhor pacote estimado', f"R$ {best['total']:,.2f}")
    b.metric('Combinações encontradas', len(results))
    c.metric('Dentro do orçamento', sum(x['total'] <= budget for x in results))
    st.subheader('Melhores combinações')
    for i, x in enumerate(results[:20]):
        with st.container(border=True):
            st.markdown(f"**{i+1}. {x['origin']} → NVT · {x['city']} · {x['start']} a {x['finish']}**")
            st.write(f"🏨 {x['hotel']} | ✈️ {x['airlines'] or 'Companhia não informada'}")
            st.write(f"Voo: R$ {x['price']:,.2f} · Hospedagem: R$ {x['total']-x['price']:,.2f} · **Total: R$ {x['total']:,.2f}**")
            if x['demo']:
                st.caption('Simulação: não é uma oferta reservável.')
            else:
                st.caption('Confirme preço final, bagagens, ocupação do quarto, taxas e traslado antes da compra.')
                if x.get('link'):
                    st.link_button('Abrir pesquisa do voo', x['link'])
            if not x['demo'] and x['total'] <= budget and st.button('Enviar alerta por e-mail', key=x['signature']):
                try:
                    ok, message = email_alert(x, budget)
                    (st.success if ok else st.warning)(message)
                except Exception as exc:
                    st.error(f'Falha no envio: {exc}')
else:
    st.info('Configure os filtros na lateral e clique em “Pesquisar pacotes”.')

st.subheader('Histórico')
with db() as conn:
    rows = conn.execute('SELECT checked_at, departure, city, start, finish, total, source FROM history ORDER BY id DESC LIMIT 30').fetchall()
if rows:
    st.dataframe([{'Consulta':r[0], 'Origem':r[1], 'Cidade':r[2], 'Ida':r[3], 'Volta':r[4], 'Total (R$)':r[5], 'Fonte':r[6]} for r in rows], use_container_width=True)
else:
    st.caption('O histórico aparece depois da primeira pesquisa.')
