# Radar de Viagens — MVP

Aplicação Streamlit para pesquisar voos de São Paulo (GRU, CGH, VCP) para Navegantes (NVT), consultar hospedagens em cidades próximas, combinar valores, registrar histórico SQLite e enviar alertas por e-mail.

## Instalação

1. Instale Python 3.10 ou superior.
2. Abra um terminal nesta pasta.
3. Execute `python -m pip install -r requirements.txt`.
4. Copie `.env.example` para `.env` e preencha `SERPAPI_KEY` para pesquisas reais.
5. Execute `streamlit run app.py`.
6. Abra o endereço local exibido pelo Streamlit. No celular, hospede o aplicativo em um servidor ou serviço de deploy.

Sem a chave de API, use o modo demonstração. **Todos os preços demonstrativos são fictícios.**

## Alertas automáticos

Preencha SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD e ALERT_TO no `.env`. Para Gmail, normalmente use uma senha de app, não sua senha normal. Execute `python monitor.py` manualmente para testar. Para executar automaticamente, configure cron, Agendador de Tarefas ou um job de servidor. O monitor de exemplo consulta apenas uma data (30 dias à frente), 4 noites, e envia e-mail para ofertas abaixo de `BUDGET` (padrão R$ 2500). Variáveis opcionais: `ADULTS` e `CHILDREN`. Agendar mais buscas aumenta consumo de API.

## Limitações importantes

- A SerpApi é um serviço externo, com limites e possível cobrança. Os parâmetros e estrutura das respostas podem mudar; ajuste o adaptador em `radar.py` quando necessário.
- A pesquisa de datas flexíveis no painel usa até 8 combinações amostradas, **não todos os dias**. A execução pode consumir várias chamadas por combinação.
- Google Flights geralmente informa tarifa para o grupo de passageiros selecionado; Google Hotels informa o valor da estadia para a ocupação consultada. **Verifique os valores finais**: o preço da hospedagem pode representar apenas um quarto, e a ocupação com crianças pode exigir condições específicas.
- A soma não inclui bagagem adicional, deslocamentos, estacionamento, ingressos do Beto Carrero, alimentação ou eventuais taxas não incluídas na fonte.
- Links de voos podem ser apenas links para a pesquisa; links de hotel podem não estar disponíveis. Confirme tudo na página do fornecedor.
- As pesquisas de voo e hospedagem são independentes; a combinação é uma estimativa, não um pacote emitido ou garantido.
- O SQLite é local ao ambiente em que o aplicativo roda; hospedagens efêmeras podem apagar o histórico. Use armazenamento persistente no deploy.
- O envio de alertas automáticos só funciona enquanto um agendador externo estiver executando `monitor.py`.
- **Segurança:** não publique o arquivo `.env` nem compartilhe credenciais. Em hospedagem pública, proteja o painel com autenticação.

## Próximas melhorias

Comparação de custo por pessoa, ocupação de múltiplos quartos, calendário diário completo, aeroportos alternativos de destino, traslado terrestre, alertas Telegram, painel de queda percentual e deploy persistente.
