# MCM Engine — Descrizione del Prodotto per Comunicazioni
*BHAVE Platform · Versione Flask 2.0*

---

## Cos'è MCM Engine

MCM Engine è una piattaforma di analytics avanzata progettata per i team di marketing dell'industria farmaceutica. Trasforma i dati di ricerca HCP (Healthcare Professionals) in insight azionabili sul comportamento, le performance e le tendenze dei canali di comunicazione medico-scientifica.

La piattaforma è organizzata in **4 aree tematiche**, ciascuna pensata per rispondere a domande strategiche specifiche e supportare decisioni di multichannel marketing basate sui dati.

---

## 1. Comportamento HCP

### Cosa trova l'utente
Un centro di analisi completo sul comportamento dei medici rispetto ai canali di comunicazione. L'utente seleziona il segmento di specializzazione (es. Cardiologi, Oncologi, Diabetologi) e ottiene in pochi secondi una fotografia precisa di come gli HCP interagiscono con ciascuno dei 20 canali disponibili: dall'ISF faccia a faccia ai webinar, dalle newsletter alle app di messaggistica.

L'area è organizzata in quattro sezioni navigabili:

- **KPI Canali** — Penetrazione, Utilità, Ricordo, Ingaggio, Propensione e NPS per canale, con visualizzazioni a barre orizzontali ordinate per impatto. Una barra di sintesi in testa alla pagina mostra i 4 KPI chiave a colpo d'occhio.
- **Mappe** — Due scatter plot che posizionano ogni canale in una matrice quadrante (es. Utilità vs Penetrazione, Ingaggio vs Utilità), rivelando subito quali canali sono "campioni nascosti" e quali necessitano di revisione strategica.
- **Funnel HCP** — Una visualizzazione del customer journey medico: dal canale di contatto fino all'alta propensione al consiglio. Include una matrice di funnel per canale, un diagramma Sankey che mostra i flussi di ricordo e ingaggio, e le combinazioni di canale con il miglior percorso OCV.
- **OCV Mix Engine** — L'analisi dell'Omnichannel Value: identifica quali combinazioni di 2 o 3 canali producono il massimo incremento del ricordo del messaggio, con una classifica dei top mix per frequenza e per OCV%.

### Come funziona
L'utente sceglie la specializzazione dal menu (con selezione multipla possibile) e clicca **"Avvia Analisi"**. Tutti i grafici si aggiornano in tempo reale. Se il campione è insufficiente per garantire affidabilità statistica, la piattaforma lo comunica chiaramente con un messaggio di avviso.

### Vantaggi
- **Decisioni immediate**: identificare in meno di un minuto quale canale performa meglio per ogni segmento di medici
- **Priorità di investimento**: la mappa quadrante mostra visivamente dove concentrare risorse e dove ridurle
- **Ottimizzazione del mix**: l'OCV Engine rivela le combinazioni di canale più efficaci, eliminando le congetture dalla pianificazione omnicanale
- **Esportazione pronta**: download in Excel con tutti i KPI su 8 fogli separati, pronto per presentazioni e report interni

---

## 2. Performance vs Mercato

### Cosa trova l'utente
Un benchmark competitivo che mette a confronto le performance di comunicazione dell'azienda focus con quelle dei competitor e del mercato nel suo complesso. L'utente seleziona l'azienda di riferimento, il segmento e i competitor da includere nell'analisi, e ottiene una visione comparativa immediata su tutti i KPI principali.

L'area è articolata in:

- **KPI Comparativi** — Grafici a barre affiancate che mostrano, canale per canale, le performance di penetrazione, ricordo e ingaggio dell'azienda rispetto al mercato e ai competitor selezionati
- **Tabellone** — Un radar chart con i 5 KPI normalizzati e una tabella comparativa analitica che evidenzia gap e vantaggi competitivi
- **Canali Enhanced** — Un'analisi avanzata per singolo canale con il dettaglio delle performance dell'azienda in relazione al benchmark di mercato

### Come funziona
L'utente seleziona l'azienda focus, i competitor da confrontare (fino a 10) e il segmento di specializzazione. La piattaforma calcola automaticamente il benchmark di mercato escludendo l'azienda di riferimento, garantendo un confronto pulito e obiettivo.

### Vantaggi
- **Posizionamento competitivo chiaro**: scoprire immediatamente su quali canali l'azienda è sopra o sotto il mercato
- **Identificazione dei gap**: individuare le aree dove i competitor performano meglio e pianificare azioni correttive
- **Visione olistica**: il radar chart permette di valutare la "forma" complessiva della performance multicanale in un unico sguardo
- **Supporto alle review strategiche**: dati strutturati per alimentare brand review, ciclo congressuale e pianificazione media

---

## 3. Trend Temporali

### Cosa trova l'utente
Una finestra temporale sulla storia della comunicazione: come sono cambiati nel tempo i KPI di penetrazione, ricordo, ingaggio, propensione e NPS per l'azienda e i suoi prodotti. L'utente può osservare l'evoluzione anno su anno (o per periodo), confrontare più prodotti sulla stessa curva e analizzare il canale per canale in ogni singolo anno.

L'area comprende:

- **Serie Storiche** — 5 grafici a linea sovrapposti che mostrano l'andamento di ciascun KPI nel tempo. L'azienda è rappresentata come linea continua; i prodotti come linee tratteggiate in colori distinti. La barra di sintesi mostra i valori dell'ultimo anno con il delta rispetto all'anno precedente (in verde o rosso)
- **Canali per Anno** — Selezionando un anno, l'utente vede i grafici a barre di penetrazione e ricordo per canale in quell'anno, più una heatmap che fotografa l'intera storia dei canali in una singola visualizzazione

### Come funziona
L'utente seleziona l'azienda e (opzionalmente) i prodotti da includere. La piattaforma carica automaticamente tutti gli anni disponibili nel dataset. Cliccando sui pulsanti anno nella sezione "Canali per Anno", le visualizzazioni si aggiornano istantaneamente. Il download Excel esporta tutta la serie storica in un file multi-foglio.

### Vantaggi
- **Memoria storica immediata**: capire in un'unica schermata se la traiettoria è positiva o negativa senza dover costruire report manuali
- **Valutazione dell'efficacia delle campagne**: correlare i picchi o i cali di KPI con le attività di marketing realizzate nei periodi corrispondenti
- **Pianificazione data-driven**: usare i trend passati per proiettare scenari futuri e definire obiettivi realistici
- **Confronto prodotti**: visualizzare in modo chiaro come si posizionano i diversi prodotti del portfolio rispetto ai KPI di brand

---

## 4. AI Agent

### Cosa trova l'utente
Un assistente conversazionale integrato direttamente nella piattaforma, capace di analizzare i dati HCP e rispondere a domande in linguaggio naturale, in italiano. L'AI Agent è alimentato da un modello di **reasoning avanzato** (deepseek-r1 via Ollama) che non si limita a rispondere, ma mostra esplicitamente il proprio processo di ragionamento prima di fornire la risposta — garantendo trasparenza e profondità analitica.

L'interfaccia include:
- **Chat conversazionale** — Input libero in italiano; l'utente può fare domande sui dati, chiedere interpretazioni, richiedere raccomandazioni strategiche
- **Pannello Ragionamento AI** — Ogni risposta include un riquadro collassabile che mostra il ragionamento passo-passo del modello ("sto analizzando la penetrazione ISF F2F, che risulta 78%, ben al di sopra della media..."), rendendo il processo interpretativo verificabile
- **Contesto dati automatico** — Con un solo clic, l'utente carica nella conversazione i dati KPI dal modulo che sta analizzando (Comportamento, Performance o Trend). L'AI utilizza quel contesto per rispondere con i numeri reali dell'analisi in corso
- **Selezione modello** — Possibilità di scegliere tra modelli con diverso bilanciamento tra velocità e accuratezza

### Come funziona
L'AI Agent gira **completamente in locale** sul computer dell'utente tramite Ollama, senza inviare dati a server esterni. Il modello riceve come contesto i KPI calcolati dalla piattaforma e risponde in modo specifico ai dati reali, non in modo generico. La risposta viene mostrata in streaming, carattere per carattere, esattamente come in una conversazione umana.

### Vantaggi
- **Interpretazione immediata**: trasformare numeri in insight narrativi senza dover costruire testi di commento manualmente
- **Privacy totale**: tutti i dati HCP e le conversazioni rimangono sul dispositivo dell'utente, senza alcun invio a cloud esterni
- **Ragionamento trasparente**: il pannello "Ragionamento AI" mostra come il modello arriva alle conclusioni, permettendo all'utente di validare o contestare l'interpretazione
- **Accelerazione del reporting**: chiedere all'AI di riassumere i punti chiave dell'analisi e usare la risposta come bozza di commento per presentazioni e report
- **Sempre disponibile**: nessuna dipendenza da API esterne, nessun costo per token, nessun limite di utilizzo

---

## Caratteristiche trasversali della piattaforma

| Caratteristica | Descrizione |
|----------------|-------------|
| **Interfaccia dark** | Design professionale ottimizzato per sessioni di lavoro prolungate e presentazioni in sala riunioni |
| **Grafici interattivi** | Tutti i grafici sono basati su Plotly.js — hover, zoom, download PNG nativi |
| **Campione minimo** | La piattaforma segnala automaticamente quando il campione è troppo piccolo per garantire affidabilità statistica (soglia: 20 HCP) |
| **Export Excel** | Ogni modulo permette il download di un file Excel multi-foglio con tutti i dati dell'analisi corrente |
| **Nomi canale standardizzati** | I 20 canali sono normalizzati con un'unica nomenclatura coerente in tutta la piattaforma |
| **Filtri per specializzazione** | Ogni analisi può essere segmentata per specializzazione medica con selezione multipla |

---

## A chi è rivolto MCM Engine

MCM Engine è progettato per professionisti del marketing farmaceutico che hanno la responsabilità di:
- Pianificare e ottimizzare il mix di canali di comunicazione medico-scientifica
- Monitorare le performance della propria azienda rispetto al mercato e ai competitor
- Presentare dati e insight ai brand team, alla leadership e agli stakeholder
- Supportare le decisioni di investimento in attività di multichannel marketing

---

*MCM Engine — BHAVE Platform · Documento per uso interno e comunicazioni commerciali*
*Versione 2.0 Flask Edition · Marzo 2026*
