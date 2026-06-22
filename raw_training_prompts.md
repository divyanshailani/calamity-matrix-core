# Calamity AI — Raw Training Prompts

> **Phase 18.1 — Zero-Cost Data Extraction**  
> Generated: `2026-06-22 16:47 UTC`  
> Total Scenarios: **50**  
> Source: Local pgvector DB + XGBoost Math Engine (No external LLM called)

---

## How to Use This File

Each scenario below is a complete, self-contained prompt.  
Copy the `### Prompt` block verbatim into your external LLM interface.  
Paste the LLM response into `### Expected Response (Fill In)`.  
When complete, these `(Prompt, Response)` pairs form the fine-tuning dataset.

---

## Scenario 01 — Earthquake | Haiti (2024)

| Field | Value |
|---|---|
| **Country** | Haiti |
| **Hazard** | Earthquake |
| **Month** | March 2024 |
| **Severity** | 6.0 / 10.0 |
| **Predicted Affected** | 6.4K |
| **Predicted Damage** | $283.8K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.6670 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Haiti
            - Hazard Type: Earthquake
            - Scenario Month: March
            - Scenario Year: 2024
            - Severity Index: 6.0 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 6.4K people
            - Estimated Economic Damage: $283.8K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Earthquake in Haiti (2018)
- **Semantic Similarity Score:** 0.6670
- **Situation Report Excerpt:**
  > A 5.9-magnitude- earthquake occurred on 6 October 2018 at 20:12 Atlantic Standard Time (AST) at a depth of 15.3 kilometres deep. According to the Haitian government’s Technical Unit of Seismology, its epicentre was located at sea in the Turtle Canal, about twenty kilometres west-northwest of Port-de-Paix in the North-West Department. Many aftershocks were felt between Saturday, 6 October 2018 and...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 02 — Cold Wave | Morocco (2020)

| Field | Value |
|---|---|
| **Country** | Morocco |
| **Hazard** | Cold Wave |
| **Month** | January 2020 |
| **Severity** | 4.1 / 10.0 |
| **Predicted Affected** | 236 |
| **Predicted Damage** | $20.0K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.7713 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Morocco
            - Hazard Type: Cold Wave
            - Scenario Month: January
            - Scenario Year: 2020
            - Severity Index: 4.1 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 236 people
            - Estimated Economic Damage: $20.0K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Cold Wave in Morocco (2017)
- **Semantic Similarity Score:** 0.7713
- **Situation Report Excerpt:**
  > From mid-January, a cold wave has moved across Morocco affecting most cities. Temperatures have fallen rapidly, reach as low as -13 degrees Celsius in high altitude areas, and between -2 and 0 degrees Celsius in the interior of the country. Regions in the east, north and south have been particularly affected. These low temperatures were due to a mass flow of polar air from the Arctic to Eastern Eu...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 03 — Epidemic | Sao Tome and Principe (2023)

| Field | Value |
|---|---|
| **Country** | Sao Tome and Principe |
| **Hazard** | Epidemic |
| **Month** | January 2023 |
| **Severity** | 5.2 / 10.0 |
| **Predicted Affected** | 3.2K |
| **Predicted Damage** | $10.1K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.6999 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Sao Tome and Principe
            - Hazard Type: Epidemic
            - Scenario Month: January
            - Scenario Year: 2023
            - Severity Index: 5.2 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 3.2K people
            - Estimated Economic Damage: $10.1K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Epidemic in Sao Tome and Principe (2022)
- **Semantic Similarity Score:** 0.6999
- **Situation Report Excerpt:**
  > On 13 May 2022, the Ministry of Public Health of Sao Tome-and-Principe reported the first outbreak of Dengue fever in Sao Tome-and-Principe to the WHO. The suspected cases started end March 2022, with recorded cases suffering from severe fever and clinical characteristics of Dengue fever. On 11 April 2022, the laboratory of the central hospital reported a suspected case of dengue fever to clinical...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 04 — Heat Wave | Syrian Arab Republic (2022)

| Field | Value |
|---|---|
| **Country** | Syrian Arab Republic |
| **Hazard** | Heat Wave |
| **Month** | December 2022 |
| **Severity** | 4.5 / 10.0 |
| **Predicted Affected** | 777 |
| **Predicted Damage** | $4.0K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.7706 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Syrian Arab Republic
            - Hazard Type: Heat Wave
            - Scenario Month: December
            - Scenario Year: 2022
            - Severity Index: 4.5 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 777 people
            - Estimated Economic Damage: $4.0K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Heat Wave in Syrian Arab Republic (2025)
- **Semantic Similarity Score:** 0.7706
- **Situation Report Excerpt:**
  > The ongoing heatwave in Syria, which began on 8 August 2025, has had a wide-reaching impact across multiple governorates, including Rural Damascus, Hama, Aleppo, Homs, Sweida, and Daraa. Temperatures have exceeded 45°C, placing immense strain on already vulnerable communities facing multiple, compounding crises — including protracted conflict, economic deterioration, displacement, and weakened inf...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 05 — Snow Avalanche | Pakistan (2025)

| Field | Value |
|---|---|
| **Country** | Pakistan |
| **Hazard** | Snow Avalanche |
| **Month** | June 2025 |
| **Severity** | 4.5 / 10.0 |
| **Predicted Affected** | 694 |
| **Predicted Damage** | $155.9K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.6929 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Pakistan
            - Hazard Type: Snow Avalanche
            - Scenario Month: June
            - Scenario Year: 2025
            - Severity Index: 4.5 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 694 people
            - Estimated Economic Damage: $155.9K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Snow Avalanche in Pakistan (2010)
- **Semantic Similarity Score:** 0.6929
- **Situation Report Excerpt:**
  > An avalanche hit villages in Qandia valley - including the Bagroo Dara, Seri and Gatloo areas - in the Kohistan District of the North-West Frontier Province on 16 February 2010. According to local resident accounts, more than 120 deaths were reported, while 220 houses comprising of approximately 1,500 - 2,000 individuals were affected in Bagroo Dara. ([Pakistan Red Crescent Society, 28 Feb 2010](h...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 06 — Mud Slide | Kyrgyzstan (2021)

| Field | Value |
|---|---|
| **Country** | Kyrgyzstan |
| **Hazard** | Mud Slide |
| **Month** | June 2021 |
| **Severity** | 4.0 / 10.0 |
| **Predicted Affected** | 6.5K |
| **Predicted Damage** | $832 |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.6902 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Kyrgyzstan
            - Hazard Type: Mud Slide
            - Scenario Month: June
            - Scenario Year: 2021
            - Severity Index: 4.0 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 6.5K people
            - Estimated Economic Damage: $832

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Mud Slide in Kyrgyzstan (2010)
- **Semantic Similarity Score:** 0.6902
- **Situation Report Excerpt:**
  > On 3 June 2010, heavy rainfall caused serious mudslides in southern Kyrgyzstan, affecting 8,350 people (1,670 households) in the Jalalabat and Osh regions. Houses, roads, cultivated lands and dams were destroyed or damaged. The most seriously affected villages were Akman and Suzak, with 1,205 families whose houses were damaged or destroyed. IFRC allocated funds on 9 June to deliver assistance to s...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 07 — Severe Local Storm | Armenia (2024)

| Field | Value |
|---|---|
| **Country** | Armenia |
| **Hazard** | Severe Local Storm |
| **Month** | December 2024 |
| **Severity** | 4.8 / 10.0 |
| **Predicted Affected** | 4.5K |
| **Predicted Damage** | $23.1K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.7279 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Armenia
            - Hazard Type: Severe Local Storm
            - Scenario Month: December
            - Scenario Year: 2024
            - Severity Index: 4.8 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 4.5K people
            - Estimated Economic Damage: $23.1K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Severe Local Storm in Armenia (2023)
- **Semantic Similarity Score:** 0.7279
- **Situation Report Excerpt:**
  > Severe hailstorms struck various regions of Armenia, causing extensive damage and disruption. On 15 June 2023, the South region, particularly rural communities near the border, experienced heavy precipitation that overwhelmed sewage systems, flooded streets and houses, and rendered roads and bridges impassable. The hail and subsequent flooding resulted in significant damage to houses, livestock, g...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 08 — Cold Wave | Serbia (2019)

| Field | Value |
|---|---|
| **Country** | Serbia |
| **Hazard** | Cold Wave |
| **Month** | September 2019 |
| **Severity** | 3.5 / 10.0 |
| **Predicted Affected** | 782.8K |
| **Predicted Damage** | $6.5K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.6957 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Serbia
            - Hazard Type: Cold Wave
            - Scenario Month: September
            - Scenario Year: 2019
            - Severity Index: 3.5 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 782.8K people
            - Estimated Economic Damage: $6.5K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Cold Wave in Serbia (2026)
- **Semantic Similarity Score:** 0.6957
- **Situation Report Excerpt:**
  > Since 4 January, severe winter weather conditions, including heavy snowfall, strong winds and low temperatures, have affected several parts of Serbia, causing partial collapse of the electricity distribution network and widespread, prolonged power outages. These outages severely disrupted heating, water supply and access to essential services, particularly in rural and hard-to-reach areas. The sit...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 09 — Tsunami | Indonesia (2019)

| Field | Value |
|---|---|
| **Country** | Indonesia |
| **Hazard** | Tsunami |
| **Month** | January 2019 |
| **Severity** | 7.7 / 10.0 |
| **Predicted Affected** | 7.7K |
| **Predicted Damage** | $551 |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.6918 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Indonesia
            - Hazard Type: Tsunami
            - Scenario Month: January
            - Scenario Year: 2019
            - Severity Index: 7.7 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 7.7K people
            - Estimated Economic Damage: $551

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Tsunami in Indonesia (2004)
- **Semantic Similarity Score:** 0.6918
- **Situation Report Excerpt:**
  > On 26 Dec 2004, the fourth-largest earthquake in a century erupted underwater off the Indonesian province of Aceh, causing a tsunami that accelerate to speeds of more than 600 kilometres per hour and barreled one-fifth of the way around the earth. More than 228,000 people died in 14 countries in Southeast Asia and South Asia, and as far away as Africa; most were women – in some places three times...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 10 — Heat Wave | Pakistan (2024)

| Field | Value |
|---|---|
| **Country** | Pakistan |
| **Hazard** | Heat Wave |
| **Month** | September 2024 |
| **Severity** | 4.6 / 10.0 |
| **Predicted Affected** | 448 |
| **Predicted Damage** | $269.3K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.7744 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Pakistan
            - Hazard Type: Heat Wave
            - Scenario Month: September
            - Scenario Year: 2024
            - Severity Index: 4.6 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 448 people
            - Estimated Economic Damage: $269.3K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Heat Wave in Pakistan (2007)
- **Semantic Similarity Score:** 0.7744
- **Situation Report Excerpt:**
  > On 14 June 2007, 57 people died across **Pakistan** due to exposure to intense heat, which raised the death toll to 289. The central province of Punjab, with an average temperature of 42 degrees Celsius, was hard hit by the hot and humid weather. People battled the sizzling temperatures amid frequent power outages as the country faced its worst ever energy crisis as electricity demand exceeded the...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 11 — Snow Avalanche | Tajikistan (2025)

| Field | Value |
|---|---|
| **Country** | Tajikistan |
| **Hazard** | Snow Avalanche |
| **Month** | November 2025 |
| **Severity** | 4.5 / 10.0 |
| **Predicted Affected** | 1.3K |
| **Predicted Damage** | $17.2K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.7496 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Tajikistan
            - Hazard Type: Snow Avalanche
            - Scenario Month: November
            - Scenario Year: 2025
            - Severity Index: 4.5 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 1.3K people
            - Estimated Economic Damage: $17.2K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Snow Avalanche in Tajikistan (2006)
- **Semantic Similarity Score:** 0.7496
- **Situation Report Excerpt:**
  > Abundant and unusual snows which fell in Tajikistan during January 2006 resulted in several disasters in the form of avalanches and mudflows in eastern and southern parts of the country. During the period from 26 January to 2 February 2006, more than 723 people were affected, 19 died, 2 were lost, 5 injured and 106 houses were totally or partially destroyed. ([IFRC, 3 Feb 2023](https://reliefweb.i...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 12 — Flood | Saint Vincent and the Grenadines (2022)

| Field | Value |
|---|---|
| **Country** | Saint Vincent and the Grenadines |
| **Hazard** | Flood |
| **Month** | June 2022 |
| **Severity** | 4.5 / 10.0 |
| **Predicted Affected** | 32.2K |
| **Predicted Damage** | $2.2K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.6896 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Saint Vincent and the Grenadines
            - Hazard Type: Flood
            - Scenario Month: June
            - Scenario Year: 2022
            - Severity Index: 4.5 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 32.2K people
            - Estimated Economic Damage: $2.2K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Flood in Saint Vincent and the Grenadines (2013)
- **Semantic Similarity Score:** 0.6896
- **Situation Report Excerpt:**
  > Severe rains and high winds due to a low level trough system caused floods and landslides in St. Vincent and the Grenadines, Saint Lucia and Dominica from 23-25 Dec 2013. St. Vincent and the Grenadines reported nine deaths and over five hundred persons affected, of which 237 were provided with emergency shelter. According to preliminary reports from initial assessments 30 homes were destroyed and...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 13 — Flood | Dominica (2025)

| Field | Value |
|---|---|
| **Country** | Dominica |
| **Hazard** | Flood |
| **Month** | February 2025 |
| **Severity** | 4.6 / 10.0 |
| **Predicted Affected** | 2.0K |
| **Predicted Damage** | $-115 |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.7081 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Dominica
            - Hazard Type: Flood
            - Scenario Month: February
            - Scenario Year: 2025
            - Severity Index: 4.6 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 2.0K people
            - Estimated Economic Damage: $-115

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Flood in Dominica (2011)
- **Semantic Similarity Score:** 0.7081
- **Situation Report Excerpt:**
  > Although Tropical Storm Ophelia did not pass directly over Dominica, it generated severe rainfall over the island affecting infrastructure and damaging personal belongings ([IFRC, 11 Oct 2011](https://reliefweb.int/node/452191)).


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 14 — Fire | Somalia (2021)

| Field | Value |
|---|---|
| **Country** | Somalia |
| **Hazard** | Fire |
| **Month** | October 2021 |
| **Severity** | 4.1 / 10.0 |
| **Predicted Affected** | 16.0K |
| **Predicted Damage** | $1.9K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.6760 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Somalia
            - Hazard Type: Fire
            - Scenario Month: October
            - Scenario Year: 2021
            - Severity Index: 4.1 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 16.0K people
            - Estimated Economic Damage: $1.9K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Fire in Somalia (2022)
- **Semantic Similarity Score:** 0.6760
- **Situation Report Excerpt:**
  > A huge fire broke out in the biggest market (Waaheen) of Hargeisa on the evening of 01 April 2022. The fire was so powerful that the Somaliland Fire Protection could only control it 16 hours after, at noon of April 02, with the support of the Ethiopia Somali region fire department. According to the Somaliland fire protection, this was the worst fire experienced in decades [...] As of April 03, SRC...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 15 — Fire | Central African Republic (2019)

| Field | Value |
|---|---|
| **Country** | Central African Republic |
| **Hazard** | Fire |
| **Month** | April 2019 |
| **Severity** | 4.5 / 10.0 |
| **Predicted Affected** | 2.0K |
| **Predicted Damage** | $624 |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.6794 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Central African Republic
            - Hazard Type: Fire
            - Scenario Month: April
            - Scenario Year: 2019
            - Severity Index: 4.5 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 2.0K people
            - Estimated Economic Damage: $624

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Fire in Central African Republic (2022)
- **Semantic Similarity Score:** 0.6794
- **Situation Report Excerpt:**
  > Two large villages located 15 km from the city of Bakala (458 km from Bangui) experienced fires in the night of 24 to 25 February 2022, which caused significant material and human damages. This area is experiencing intense drought and very high temperatures at the end of the dry season, between February and March. Moreover, this is the period during which fields go up in flames due to dryness. The...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 16 — Flash Flood | Russian Federation (2018)

| Field | Value |
|---|---|
| **Country** | Russian Federation |
| **Hazard** | Flash Flood |
| **Month** | October 2018 |
| **Severity** | 4.9 / 10.0 |
| **Predicted Affected** | 17.8K |
| **Predicted Damage** | $4.4K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.7390 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Russian Federation
            - Hazard Type: Flash Flood
            - Scenario Month: October
            - Scenario Year: 2018
            - Severity Index: 4.9 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 17.8K people
            - Estimated Economic Damage: $4.4K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Flash Flood in Russian Federation (2012)
- **Semantic Similarity Score:** 0.7390
- **Situation Report Excerpt:**
  > Torrential rains during the night of 6 Jul 2012 caused severe flash floods in Russia's southern Krasnodar region, which killed 172 people and inured almost 4,000. 3,000 people had to be evacuated, and 5,500 residents lost their property completely in the area's worst natural disaster in decades. ([IFRC, 23 Jul 2012](https://reliefweb.int/node/512516)) On 22 August 2012 in the village of Novomikhai...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 17 — Tropical Cyclone | Antigua and Barbuda (2025)

| Field | Value |
|---|---|
| **Country** | Antigua and Barbuda |
| **Hazard** | Tropical Cyclone |
| **Month** | July 2025 |
| **Severity** | 6.7 / 10.0 |
| **Predicted Affected** | 3.4K |
| **Predicted Damage** | $105.1K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.6170 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Antigua and Barbuda
            - Hazard Type: Tropical Cyclone
            - Scenario Month: July
            - Scenario Year: 2025
            - Severity Index: 6.7 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 3.4K people
            - Estimated Economic Damage: $105.1K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Tropical Cyclone in Antigua and Barbuda (2017)
- **Semantic Similarity Score:** 0.6170
- **Situation Report Excerpt:**
  > As of 1 September, [NOAA]’s National Hurricane Centre (NHC), stated that Hurricane Irma’s centre was located near latitude 18.8 north, longitude 39.1 west at 5 PM Atlantic Standard Time (AST) (2100 [UTC]). Irma was moving toward the west at around 13 mph (20 km/h). A turn toward the west-south-west was expected by 2 September 2017. Irma is a category 3 hurricane on the Saffir-Simpson Hurricane Win...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 18 — Epidemic | Congo (2022)

| Field | Value |
|---|---|
| **Country** | Congo |
| **Hazard** | Epidemic |
| **Month** | April 2022 |
| **Severity** | 6.0 / 10.0 |
| **Predicted Affected** | 457 |
| **Predicted Damage** | $1.5K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.7049 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Congo
            - Hazard Type: Epidemic
            - Scenario Month: April
            - Scenario Year: 2022
            - Severity Index: 6.0 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 457 people
            - Estimated Economic Damage: $1.5K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Epidemic in Congo (2013)
- **Semantic Similarity Score:** 0.7049
- **Situation Report Excerpt:**
  > The [heavy downpour of 17 and 18 Nov 2012](https://reliefweb.int/disaster/ff-2012-000196-cog) caused widespread destruction of the drainage system, overflowed wells and latrines as well as stagnant water in Pointe Noire, the second largest city in the Republic of Congo. A few weeks after the flooding, the first cholera case was recorded, and the numbers of cases and deaths continue to increase. As...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 19 — Drought | Moldova (2021)

| Field | Value |
|---|---|
| **Country** | Moldova |
| **Hazard** | Drought |
| **Month** | February 2021 |
| **Severity** | 4.5 / 10.0 |
| **Predicted Affected** | 53 |
| **Predicted Damage** | $3.8K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.7643 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Moldova
            - Hazard Type: Drought
            - Scenario Month: February
            - Scenario Year: 2021
            - Severity Index: 4.5 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 53 people
            - Estimated Economic Damage: $3.8K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Drought in Moldova (2012)
- **Semantic Similarity Score:** 0.7643
- **Situation Report Excerpt:**
  > In 2012, Moldova suffered the combined impacts of poor rainfall and extremely high temperatures, which resulted in major losses in the national crop production. The 2012 drought was part of a regional phenomenon, which affected large parts of the Black Sea region, the Balkans and Central Europe. On 6 Aug, the Prime Minister announced that Moldova’s agrarian sector was in an acute need of internati...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 20 — Volcano | Saint Vincent and the Grenadines (2023)

| Field | Value |
|---|---|
| **Country** | Saint Vincent and the Grenadines |
| **Hazard** | Volcano |
| **Month** | September 2023 |
| **Severity** | 5.2 / 10.0 |
| **Predicted Affected** | 8.0K |
| **Predicted Damage** | $5.4K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.6905 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Saint Vincent and the Grenadines
            - Hazard Type: Volcano
            - Scenario Month: September
            - Scenario Year: 2023
            - Severity Index: 5.2 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 8.0K people
            - Estimated Economic Damage: $5.4K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Volcano in Saint Vincent and the Grenadines (2021)
- **Semantic Similarity Score:** 0.6905
- **Situation Report Excerpt:**
  > On 29th December 2020, the alert level for the La Soufrière volcano in St. Vincent and the Grenadines was elevated to orange because of increased activity at the site...An orange level alert means that there is highly elevated seismicity or fumarolic activity, or both, and other highly unusual symptoms. Eruptions may occur with less than 24 hours’ notice. Monitoring systems are continuously staffe...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 21 — Flash Flood | Zimbabwe (2019)

| Field | Value |
|---|---|
| **Country** | Zimbabwe |
| **Hazard** | Flash Flood |
| **Month** | March 2019 |
| **Severity** | 4.9 / 10.0 |
| **Predicted Affected** | 350 |
| **Predicted Damage** | $78.5K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.7049 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Zimbabwe
            - Hazard Type: Flash Flood
            - Scenario Month: March
            - Scenario Year: 2019
            - Severity Index: 4.9 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 350 people
            - Estimated Economic Damage: $78.5K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Flash Flood in Zimbabwe (2014)
- **Semantic Similarity Score:** 0.7049
- **Situation Report Excerpt:**
  > Heavy rains in parts of Zimbabwe in late January and early February 2014 resulted in deaths and displacement of people, coupled with destruction of property. The worst affected areas were Chivi and Masvingo districts in Masvingo province and Tsholotsho district in Matabeleland North ([OCHA, 07 Feb 2014](https://reliefweb.int/report/zimbabwe/zimbambwe-flash-flood-update-1-7-february-2014)). On 11 F...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 22 — Wild Fire | Bolivia (Plurinational State of) (2023)

| Field | Value |
|---|---|
| **Country** | Bolivia (Plurinational State of) |
| **Hazard** | Wild Fire |
| **Month** | May 2023 |
| **Severity** | 3.8 / 10.0 |
| **Predicted Affected** | 5.6K |
| **Predicted Damage** | $5.1K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.6936 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Bolivia (Plurinational State of)
            - Hazard Type: Wild Fire
            - Scenario Month: May
            - Scenario Year: 2023
            - Severity Index: 3.8 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 5.6K people
            - Estimated Economic Damage: $5.1K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Wild Fire in Bolivia (Plurinational State of) (2024)
- **Semantic Similarity Score:** 0.6936
- **Situation Report Excerpt:**
  > On 24 July 2024, the Bolivia Ministry of Defense (MINDEF per its acronym in Spanish) published information on wildfires occurring in Bolivia. MINDEF is reporting 11,576 hotspots distributed throughout the national territory (6,671 increase since the 17 July report), of which, almost 96% are in the departments of Santa Cruz and Beni. Additionally, 20 wildfires were contained (6 increase). A total o...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 23 — Volcano | USA (2025)

| Field | Value |
|---|---|
| **Country** | USA |
| **Hazard** | Volcano |
| **Month** | December 2025 |
| **Severity** | 5.4 / 10.0 |
| **Predicted Affected** | 1.0K |
| **Predicted Damage** | $2.6K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | -0.0047 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: USA
            - Hazard Type: Volcano
            - Scenario Month: December
            - Scenario Year: 2025
            - Severity Index: 5.4 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 1.0K people
            - Estimated Economic Damage: $2.6K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Volcano in USA (1980)
- **Semantic Similarity Score:** -0.0047
- **Situation Report Excerpt:**
  > Mount St. Helens eruption.


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 24 — Cold Wave | Bulgaria (2021)

| Field | Value |
|---|---|
| **Country** | Bulgaria |
| **Hazard** | Cold Wave |
| **Month** | December 2021 |
| **Severity** | 4.0 / 10.0 |
| **Predicted Affected** | 416 |
| **Predicted Damage** | $9.9K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.7076 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Bulgaria
            - Hazard Type: Cold Wave
            - Scenario Month: December
            - Scenario Year: 2021
            - Severity Index: 4.0 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 416 people
            - Estimated Economic Damage: $9.9K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Cold Wave in Bulgaria (2009)
- **Semantic Similarity Score:** 0.7076
- **Situation Report Excerpt:**
  > From northern Europe to the Balkans, weather officials reported temperatures plunging overnight to as low as minus 30 degrees Celsius, while further snowfalls created havoc with rail services and left motorists stranded for hours on icy and snow-covered roads. In Warsaw, police officials said 15 people froze to death on Saturday alone, bringing to 57 the number of people who have died in Poland fr...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 25 — Severe Local Storm | Cuba (2023)

| Field | Value |
|---|---|
| **Country** | Cuba |
| **Hazard** | Severe Local Storm |
| **Month** | July 2023 |
| **Severity** | 5.1 / 10.0 |
| **Predicted Affected** | 1.2K |
| **Predicted Damage** | $30.6K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.7259 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Cuba
            - Hazard Type: Severe Local Storm
            - Scenario Month: July
            - Scenario Year: 2023
            - Severity Index: 5.1 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 1.2K people
            - Estimated Economic Damage: $30.6K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Severe Local Storm in Cuba (2020)
- **Semantic Similarity Score:** 0.7259
- **Situation Report Excerpt:**
  > On 25 to 26 May, a severe local storm brought tornados, hail falls, waterspouts and linear winds over 92 km/h. A tornado event was registered in the province of Santi Spiritus with winds of 120 km/h. According to the Provincial Meteorological Centre in Sancti Spiritus the tornado was the most visible event of larger severe storms affecting the area. Other severe local storms also significantly imp...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 26 — Flood | Mauritania (2018)

| Field | Value |
|---|---|
| **Country** | Mauritania |
| **Hazard** | Flood |
| **Month** | June 2018 |
| **Severity** | 4.5 / 10.0 |
| **Predicted Affected** | 2.8K |
| **Predicted Damage** | $1.3K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.7480 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Mauritania
            - Hazard Type: Flood
            - Scenario Month: June
            - Scenario Year: 2018
            - Severity Index: 4.5 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 2.8K people
            - Estimated Economic Damage: $1.3K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Flood in Mauritania (2022)
- **Semantic Similarity Score:** 0.7480
- **Situation Report Excerpt:**
  > From 25 July to 3rd August 2022, heavy rains caused flooding in some parts of Mauritania, including Hodh El Gharbi, Assaba and Tagant in southern and central Mauritania. Among other things, the floods caused extensive material damage to 4,351 households, or 28,926 people. They also caused the deaths of 14 people, most of them are children. Across all the 7 affected regions, 3,817 houses were destr...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 27 — Extratropical Cyclone | China (2020)

| Field | Value |
|---|---|
| **Country** | China |
| **Hazard** | Extratropical Cyclone |
| **Month** | January 2020 |
| **Severity** | 5.2 / 10.0 |
| **Predicted Affected** | 787 |
| **Predicted Damage** | $3.80M |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.7211 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: China
            - Hazard Type: Extratropical Cyclone
            - Scenario Month: January
            - Scenario Year: 2020
            - Severity Index: 5.2 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 787 people
            - Estimated Economic Damage: $3.80M

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Extratropical Cyclone in China (1997)
- **Semantic Similarity Score:** 0.7211
- **Situation Report Excerpt:**
  > **China** On 18 August, Typhoon Winnie made landfall in China, Zhejiang Province, giving rise to rainfall over 200 mm. The typhoon arrived at a time when there was high tide, reaching the highest level in history. The sea embankment at Taizhou City was destroyed and sea water submerged a large stretch of farmland. The sea embankment at Wenzhou, Ningbo and Zhoushan were also severely damaged, part...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 28 — Drought | Indonesia (2023)

| Field | Value |
|---|---|
| **Country** | Indonesia |
| **Hazard** | Drought |
| **Month** | June 2023 |
| **Severity** | 5.0 / 10.0 |
| **Predicted Affected** | 268.9K |
| **Predicted Damage** | $51.5K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.6868 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Indonesia
            - Hazard Type: Drought
            - Scenario Month: June
            - Scenario Year: 2023
            - Severity Index: 5.0 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 268.9K people
            - Estimated Economic Damage: $51.5K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Drought in Indonesia (2023)
- **Semantic Similarity Score:** 0.6868
- **Situation Report Excerpt:**
  > The El Niño phenomenon has contributed to a prolonged dry season, resulting in crop failure and drought in the Agandugume and Lambewi sub-districts in Puncak District, Central Papua Province. An Emergency Response Status for drought events in the affected sub-districts was declared by the Regent of Puncak District, effective from 7 June to 7 August 2023. According to Regional Disaster Management A...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 29 — Epidemic | Papua New Guinea (2023)

| Field | Value |
|---|---|
| **Country** | Papua New Guinea |
| **Hazard** | Epidemic |
| **Month** | September 2023 |
| **Severity** | 5.6 / 10.0 |
| **Predicted Affected** | 381 |
| **Predicted Damage** | $162.3K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.6743 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Papua New Guinea
            - Hazard Type: Epidemic
            - Scenario Month: September
            - Scenario Year: 2023
            - Severity Index: 5.6 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 381 people
            - Estimated Economic Damage: $162.3K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Epidemic in Papua New Guinea (2025)
- **Semantic Similarity Score:** 0.6743
- **Situation Report Excerpt:**
  > On 15 May 2025 Papua New Guinea (PNG) confirmed a polio outbreak—the first since 2018—after detecting two cases of poliovirus type 2 in children from Lae, Morobe Province. Environmental samples from Port Moresby also tested positive for the virus, indicating community transmission. Genetic sequencing linked the strain to poliovirus that was circulating in Indonesia. ([WHO, 19 May 2025](https://rel...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 30 — Snow Avalanche | Afghanistan (2022)

| Field | Value |
|---|---|
| **Country** | Afghanistan |
| **Hazard** | Snow Avalanche |
| **Month** | December 2022 |
| **Severity** | 3.8 / 10.0 |
| **Predicted Affected** | 521 |
| **Predicted Damage** | $1.8K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.7272 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Afghanistan
            - Hazard Type: Snow Avalanche
            - Scenario Month: December
            - Scenario Year: 2022
            - Severity Index: 3.8 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 521 people
            - Estimated Economic Damage: $1.8K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Snow Avalanche in Afghanistan (2012)
- **Semantic Similarity Score:** 0.7272
- **Situation Report Excerpt:**
  > Starting in January 2012, Afghanistan experienced its most severe winter in 15 years, characterized by above-average snowfall and temperatures descending to -18 degrees Celsius in some areas. 43 people died and 65 were injured as a result of avalanches and extreme cold temperatures in 10 districts of Badakhshan province ([OCHA, 31 Jan 2012](https://reliefweb.int/node/477988)). In February, 54 chil...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 31 — Drought | Ethiopia (2021)

| Field | Value |
|---|---|
| **Country** | Ethiopia |
| **Hazard** | Drought |
| **Month** | January 2021 |
| **Severity** | 4.7 / 10.0 |
| **Predicted Affected** | 28.6K |
| **Predicted Damage** | $172.2K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.6898 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Ethiopia
            - Hazard Type: Drought
            - Scenario Month: January
            - Scenario Year: 2021
            - Severity Index: 4.7 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 28.6K people
            - Estimated Economic Damage: $172.2K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Drought in Ethiopia (2017)
- **Semantic Similarity Score:** 0.6898
- **Situation Report Excerpt:**
  > While Ethiopia battles residual needs from the 2015/2016 El Niño-induced drought, below average 2016 autumn rains in the southern and southeastern parts of the country have led to a new drought in lowland pastoralist areas, as well as in pocket areas across the country. As a result, some 5.6 million people in Ethiopia require emergency food assistance in 2017. In addition, 2.7 million children and...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 32 — Land Slide | Pakistan (2022)

| Field | Value |
|---|---|
| **Country** | Pakistan |
| **Hazard** | Land Slide |
| **Month** | May 2022 |
| **Severity** | 4.8 / 10.0 |
| **Predicted Affected** | 208 |
| **Predicted Damage** | $477.1K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.6347 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Pakistan
            - Hazard Type: Land Slide
            - Scenario Month: May
            - Scenario Year: 2022
            - Severity Index: 4.8 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 208 people
            - Estimated Economic Damage: $477.1K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Land Slide in Pakistan (2010)
- **Semantic Similarity Score:** 0.6347
- **Situation Report Excerpt:**
  > The Hunza Valley (in Gilgit Baltistan) received heavy land sliding on 4 January 2010, killing 19 people. One village was destroyed by the immediate effects of the landslides. The Pakistan Red Crescent Society's Gilgit Baltistan branch started relief operations right after the landslides. The national society provided food and non-food items to at least 332 affected households. ([IFRC, 14 Jan 2010]...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 33 — Extratropical Cyclone | Republic of Korea (2024)

| Field | Value |
|---|---|
| **Country** | Republic of Korea |
| **Hazard** | Extratropical Cyclone |
| **Month** | November 2024 |
| **Severity** | 5.4 / 10.0 |
| **Predicted Affected** | 5.6K |
| **Predicted Damage** | $3.0K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.7271 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Republic of Korea
            - Hazard Type: Extratropical Cyclone
            - Scenario Month: November
            - Scenario Year: 2024
            - Severity Index: 5.4 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 5.6K people
            - Estimated Economic Damage: $3.0K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Extratropical Cyclone in Republic of Korea (1987)
- **Semantic Similarity Score:** 0.7271
- **Situation Report Excerpt:**
  > Since 16 July, two devastating catastrophes have hit the Republic of Korea, namely Typhoon Thelma, and the heavy storms resulting in floods and landslides. Typhoon Thelma, which swept across the southern coast with winds reaching 130 kph, caused enormous devastation. More than 300 people were reported dead or missing and over 20,000 were made homeless. On 22/23 July, torrential non-stop rain fell...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 34 — Mud Slide | Peru (2023)

| Field | Value |
|---|---|
| **Country** | Peru |
| **Hazard** | Mud Slide |
| **Month** | May 2023 |
| **Severity** | 4.4 / 10.0 |
| **Predicted Affected** | 15.1K |
| **Predicted Damage** | $8.0K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.5946 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Peru
            - Hazard Type: Mud Slide
            - Scenario Month: May
            - Scenario Year: 2023
            - Severity Index: 4.4 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 15.1K people
            - Estimated Economic Damage: $8.0K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Mud Slide in Peru (2011)
- **Semantic Similarity Score:** 0.5946
- **Situation Report Excerpt:**
  > The Government declared a 60 day State of Emergency for five provinces in the Department of ICA affected by floods. This declaration facilitates actions aimed at reducing and minimizing existing risks and responding to affected populations. Rains caused rivers to overflow in the departments of Arequipa, Ayacucho, Puno, Ucayali, Huancavelica, damaging homes, crops and infrastructures. In Arequipa a...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 35 — Land Slide | Uganda (2023)

| Field | Value |
|---|---|
| **Country** | Uganda |
| **Hazard** | Land Slide |
| **Month** | August 2023 |
| **Severity** | 4.2 / 10.0 |
| **Predicted Affected** | 91 |
| **Predicted Damage** | $7.6K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.6485 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Uganda
            - Hazard Type: Land Slide
            - Scenario Month: August
            - Scenario Year: 2023
            - Severity Index: 4.2 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 91 people
            - Estimated Economic Damage: $7.6K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Land Slide in Uganda (2012)
- **Semantic Similarity Score:** 0.6485
- **Situation Report Excerpt:**
  > 18 people were confirmed dead and nine injured by landslides that burried two villages of Namaaga and Bunakasala in Bumwalukani Sub County, Bududa District, on 25 Jun 2012 ([Uganda Red Cross, 26 Jun 2012](https://reliefweb.int/node/506301)). Sunday 24th June 2012, a landslide caused by heavy rains buried the villages of Namanga and Bunakasala in Bududa district. The landslide covered approximately...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 36 — Land Slide | Bangladesh (2018)

| Field | Value |
|---|---|
| **Country** | Bangladesh |
| **Hazard** | Land Slide |
| **Month** | March 2018 |
| **Severity** | 4.5 / 10.0 |
| **Predicted Affected** | 520 |
| **Predicted Damage** | $4.7K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.6173 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Bangladesh
            - Hazard Type: Land Slide
            - Scenario Month: March
            - Scenario Year: 2018
            - Severity Index: 4.5 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 520 people
            - Estimated Economic Damage: $4.7K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Land Slide in Bangladesh (2017)
- **Semantic Similarity Score:** 0.6173
- **Situation Report Excerpt:**
  > Deadly mudslides triggered by torrential monsoon rains in southeastern Bangladesh are estimated to have claimed at least 135 lives. This disaster occurred just two weeks after Cyclone Mora killed 9 people and caused significant damage across the region. In addition to mudslides, the rains caused severe flooding in low-lying areas, causing significant damage to road and communication infrastructure...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 37 — Fire | Guinea-Bissau (2025)

| Field | Value |
|---|---|
| **Country** | Guinea-Bissau |
| **Hazard** | Fire |
| **Month** | March 2025 |
| **Severity** | 4.4 / 10.0 |
| **Predicted Affected** | 8.6K |
| **Predicted Damage** | $129 |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.7081 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Guinea-Bissau
            - Hazard Type: Fire
            - Scenario Month: March
            - Scenario Year: 2025
            - Severity Index: 4.4 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 8.6K people
            - Estimated Economic Damage: $129

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Fire in Guinea-Bissau (2023)
- **Semantic Similarity Score:** 0.7081
- **Situation Report Excerpt:**
  > In the morning hours of January 14, 2023, a fire broke out in Menegue Village close to Canhabaque that destroyed dozens houses and along with food stock, crops and seeds. According to findings from a rapid assessment of Guinea Bissau Red Cross on 19th January, the fire incident has affected 295 Households (2065 people). ([IFRC, 1 Feb 2023](https://reliefweb.int/node/3929049))


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 38 — Mud Slide | Colombia (2024)

| Field | Value |
|---|---|
| **Country** | Colombia |
| **Hazard** | Mud Slide |
| **Month** | July 2024 |
| **Severity** | 4.4 / 10.0 |
| **Predicted Affected** | 2.1K |
| **Predicted Damage** | $8.5K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.6740 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Colombia
            - Hazard Type: Mud Slide
            - Scenario Month: July
            - Scenario Year: 2024
            - Severity Index: 4.4 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 2.1K people
            - Estimated Economic Damage: $8.5K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Mud Slide in Colombia (2017)
- **Semantic Similarity Score:** 0.6740
- **Situation Report Excerpt:**
  > On the night of 31 March 2017, increased rainfall caused the Mocoa, Sangoyaco and Mulata Rivers to overflow, which in turn generated a mudslide in the municipality of Mocoa, capital of the department of Putumayo. UNGRD reported that the affected area received 33 per cent of its monthly total of rainfall (130 mm of the 400-mm monthly average) on the night of the disaster. Per reports, 273 people pe...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 39 — Earthquake | Guatemala (2020)

| Field | Value |
|---|---|
| **Country** | Guatemala |
| **Hazard** | Earthquake |
| **Month** | July 2020 |
| **Severity** | 6.4 / 10.0 |
| **Predicted Affected** | 5.0K |
| **Predicted Damage** | $209.1K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.7398 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Guatemala
            - Hazard Type: Earthquake
            - Scenario Month: July
            - Scenario Year: 2020
            - Severity Index: 6.4 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 5.0K people
            - Estimated Economic Damage: $209.1K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Earthquake in Guatemala (2025)
- **Semantic Similarity Score:** 0.7398
- **Situation Report Excerpt:**
  > Since 8 July, a series of earthquakes has severely affected several departments of Guatemala, causing significant impacts on both the population and infrastructure. According to the latest report from the National Coordinator for Disaster Reduction (CONRED), updated as of 16 July, a total of 14,541 people — approximately 4,450 families — have been directly affected. The emergency has forced the ev...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 40 — Earthquake | Japan (2019)

| Field | Value |
|---|---|
| **Country** | Japan |
| **Hazard** | Earthquake |
| **Month** | January 2019 |
| **Severity** | 6.7 / 10.0 |
| **Predicted Affected** | 5.6K |
| **Predicted Damage** | $325.0K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.6977 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Japan
            - Hazard Type: Earthquake
            - Scenario Month: January
            - Scenario Year: 2019
            - Severity Index: 6.7 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 5.6K people
            - Estimated Economic Damage: $325.0K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Earthquake in Japan (2011)
- **Semantic Similarity Score:** 0.6977
- **Situation Report Excerpt:**
  > On 11 Mar 2011, a massive tsunami was triggered by a 9.0 magnitude earthquake in northeast Japan, causing widespread destruction. The tsunami was up to 30 meters high and inundated 433,000 square kilometers of land. 492,000 people were evacuated, 11,600 were killed and 16,450 were reported missing. 17,000 homes and buildings were destroyed and 138,000 damaged. ([OCHA, 1 Apr 2011](https://reliefweb...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 41 — Tropical Cyclone | Mozambique (2024)

| Field | Value |
|---|---|
| **Country** | Mozambique |
| **Hazard** | Tropical Cyclone |
| **Month** | May 2024 |
| **Severity** | 7.0 / 10.0 |
| **Predicted Affected** | 276 |
| **Predicted Damage** | $12.5K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.7158 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Mozambique
            - Hazard Type: Tropical Cyclone
            - Scenario Month: May
            - Scenario Year: 2024
            - Severity Index: 7.0 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 276 people
            - Estimated Economic Damage: $12.5K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Tropical Cyclone in Mozambique (2024)
- **Semantic Similarity Score:** 0.7158
- **Situation Report Excerpt:**
  > The National Institute for Disaster Management (INGD) report that 48,116 people (8,533 households) were affected in the provinces of Gaza, Inhambane, Maputo and Sofala. Two deaths and 25 people injured have been reported. According to the information available, the most affected area is Maputo city with 25,455 people affected (2 percent of total population). Damage to infrastructure includes 8,000...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 42 — Tsunami | Solomon Islands (2025)

| Field | Value |
|---|---|
| **Country** | Solomon Islands |
| **Hazard** | Tsunami |
| **Month** | July 2025 |
| **Severity** | 7.2 / 10.0 |
| **Predicted Affected** | 22.9K |
| **Predicted Damage** | $2.0K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.7324 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Solomon Islands
            - Hazard Type: Tsunami
            - Scenario Month: July
            - Scenario Year: 2025
            - Severity Index: 7.2 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 22.9K people
            - Estimated Economic Damage: $2.0K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Tsunami in Solomon Islands (2007)
- **Semantic Similarity Score:** 0.7324
- **Situation Report Excerpt:**
  > An earthquake measuring 8.1 on the Richter scale struck 345km northwest of the Solomon Islands' capital Honiara at 0740 local time on 2 April (2040 GMT 1 April). The earthquake created a tsunami, which caused casualties and significant damage to Gizo, Simbo, Ranogga, Shortland Islands, Munda, Noro, Vella la Vella, Kolombangarra and parts of the southern coast of Choiseul. As of 16 April, the offic...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 43 — Storm Surge | Marshall Islands (2022)

| Field | Value |
|---|---|
| **Country** | Marshall Islands |
| **Hazard** | Storm Surge |
| **Month** | November 2022 |
| **Severity** | 5.2 / 10.0 |
| **Predicted Affected** | 885 |
| **Predicted Damage** | $3.0K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.7207 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Marshall Islands
            - Hazard Type: Storm Surge
            - Scenario Month: November
            - Scenario Year: 2022
            - Severity Index: 5.2 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 885 people
            - Estimated Economic Damage: $3.0K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Storm Surge in Marshall Islands (2024)
- **Semantic Similarity Score:** 0.7207
- **Situation Report Excerpt:**
  > On the night of 22 January 2024, a significant water and wave-related event occurred due to a potent winter storm system in the far northern Pacific. This event primarily impacted the Marshall Islands, particularly the Roi Namur Islet in the northern sector of Kwajalein Atoll, which is part of the US Military base. Notably, this incident involved weather-driven waves and inundation, distinct from...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 44 — Flash Flood | Sierra Leone (2025)

| Field | Value |
|---|---|
| **Country** | Sierra Leone |
| **Hazard** | Flash Flood |
| **Month** | December 2025 |
| **Severity** | 5.4 / 10.0 |
| **Predicted Affected** | 36.7K |
| **Predicted Damage** | $923 |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.7164 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Sierra Leone
            - Hazard Type: Flash Flood
            - Scenario Month: December
            - Scenario Year: 2025
            - Severity Index: 5.4 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 36.7K people
            - Estimated Economic Damage: $923

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Flash Flood in Sierra Leone (2022)
- **Semantic Similarity Score:** 0.7164
- **Situation Report Excerpt:**
  > Freetown, the capital city of Sierra Leone has been experiencing persistent torrential rains since mid-August 2022. The highest recorded incident was on 28 August 2022, with rains causing associated impacts, including flooding in low-lying areas as well as new episodes of landslides on a low scale. Major roads in the city centre were rendered impassable due to the flood waters, heavily constrainin...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 45 — Wild Fire | Ecuador (2023)

| Field | Value |
|---|---|
| **Country** | Ecuador |
| **Hazard** | Wild Fire |
| **Month** | June 2023 |
| **Severity** | 3.9 / 10.0 |
| **Predicted Affected** | 7.2K |
| **Predicted Damage** | $884 |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.7147 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Ecuador
            - Hazard Type: Wild Fire
            - Scenario Month: June
            - Scenario Year: 2023
            - Severity Index: 3.9 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 7.2K people
            - Estimated Economic Damage: $884

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Wild Fire in Ecuador (2012)
- **Semantic Similarity Score:** 0.7147
- **Situation Report Excerpt:**
  > Ecuador experienced 2,912 wild fires between June and September 2012, with an average of 26 large-scale fires per day. Three deaths were reported and over 15,000 hectares of land were incinerated. On 13 Sep, the Government declared an orange alert in eight of the country’s provinces through [decree No. SNGR-033-2012](https://reliefweb.int/report/ecuador/la-secretar%C3%ADa-nacional-de-gesti%C3%B3n-...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 46 — Extratropical Cyclone | Pakistan (2021)

| Field | Value |
|---|---|
| **Country** | Pakistan |
| **Hazard** | Extratropical Cyclone |
| **Month** | August 2021 |
| **Severity** | 5.3 / 10.0 |
| **Predicted Affected** | 224 |
| **Predicted Damage** | $279.6K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.6778 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Pakistan
            - Hazard Type: Extratropical Cyclone
            - Scenario Month: August
            - Scenario Year: 2021
            - Severity Index: 5.3 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 224 people
            - Estimated Economic Damage: $279.6K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Extratropical Cyclone in Pakistan (1999)
- **Semantic Similarity Score:** 0.6778
- **Situation Report Excerpt:**
  > More than 200 people are dead after a cyclone hit the south-eastern coast of Pakistan on 20 May, with winds of up to 270 kms per hour. People drowned or were crushed to death as their houses collapsed in the strong winds and tidal waves. It is estimated some 500,000 people have been affected by the cyclone, but these figures are still unconfirmed due to the inaccessibility of the affected region....


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 47 — Hurricane | USA (2020)

| Field | Value |
|---|---|
| **Country** | USA |
| **Hazard** | Hurricane |
| **Month** | December 2020 |
| **Severity** | 7.3 / 10.0 |
| **Predicted Affected** | 65 |
| **Predicted Damage** | $10.0K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | -0.0041 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: USA
            - Hazard Type: Hurricane
            - Scenario Month: December
            - Scenario Year: 2020
            - Severity Index: 7.3 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 65 people
            - Estimated Economic Damage: $10.0K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Hurricane in USA (2005)
- **Semantic Similarity Score:** -0.0041
- **Situation Report Excerpt:**
  > Hurricane Katrina struck the Gulf Coast.


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 48 — Heat Wave | Democratic People's Republic of Korea (2024)

| Field | Value |
|---|---|
| **Country** | Democratic People's Republic of Korea |
| **Hazard** | Heat Wave |
| **Month** | June 2024 |
| **Severity** | 4.7 / 10.0 |
| **Predicted Affected** | 1.4K |
| **Predicted Damage** | $1.3K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.7192 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Democratic People's Republic of Korea
            - Hazard Type: Heat Wave
            - Scenario Month: June
            - Scenario Year: 2024
            - Severity Index: 4.7 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 1.4K people
            - Estimated Economic Damage: $1.3K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Heat Wave in Democratic People's Republic of Korea (2018)
- **Semantic Similarity Score:** 0.7192
- **Situation Report Excerpt:**
  > According to the DPRK state media, Korean Workers' Party newspaper Rodong Sinmun, an emergency response was declared on 2 August 2018 because of unusually hot weather. On the same day, DPRK RCS officially informed IFRC of a developing slow onset emergency in both South Pyongan and South Hamgyong provinces due to a heat wave affecting the Korean Peninsula that has also severely affected the routine...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 49 — Storm Surge | Madagascar (2020)

| Field | Value |
|---|---|
| **Country** | Madagascar |
| **Hazard** | Storm Surge |
| **Month** | July 2020 |
| **Severity** | 5.7 / 10.0 |
| **Predicted Affected** | 264 |
| **Predicted Damage** | $15.6K |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.7158 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Madagascar
            - Hazard Type: Storm Surge
            - Scenario Month: July
            - Scenario Year: 2020
            - Severity Index: 5.7 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 264 people
            - Estimated Economic Damage: $15.6K

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Storm Surge in Madagascar (2010)
- **Semantic Similarity Score:** 0.7158
- **Situation Report Excerpt:**
  > On 10 Mar 2010, Cyclone Hubert hit the East Coast of Madagascar. The moderate cyclone was accompanied by heavy rainfall, which caused flooding in seven districts namely Nosy Varika, Mananjary, Manakara, Vohipeno, Farafangana, Vangaindrano (south east) and Ambatondrazaka (middle east) districts. 192,000 persons were affected, 85 deaths were reported, 132 people were wounded and 35 people went missi...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Scenario 50 — Severe Local Storm | Lebanon (2022)

| Field | Value |
|---|---|
| **Country** | Lebanon |
| **Hazard** | Severe Local Storm |
| **Month** | February 2022 |
| **Severity** | 5.2 / 10.0 |
| **Predicted Affected** | 2.1K |
| **Predicted Damage** | $90.76M |
| **RAG Analogy** | ✅ Found |
| **Analogy Similarity** | 0.6508 |

### Prompt

```
You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb.

            A simulation has been run for the following scenario. Using the Math Engine predictions and historical context provided, generate a structured, grounded impact assessment.

            **Simulation Parameters:**
            - Location: Lebanon
            - Hazard Type: Severe Local Storm
            - Scenario Month: February
            - Scenario Year: 2022
            - Severity Index: 5.2 / 10.0

            **Math Engine Predictions (XGBoost):**
            - Estimated Affected Population: 2.1K people
            - Estimated Economic Damage: $90.76M

            **Closest Historical Analogy (RAG Engine):**
            - **Historical Event:** Severe Local Storm in Lebanon (2018)
- **Semantic Similarity Score:** 0.6508
- **Situation Report Excerpt:**
  > Qatar Red Crescent Society (QRCS) has responded to the heavy rain and subsequent floods in **northern Syria**, which affected thousands of internally displaced people (IDPs) in 22 camps across five towns of Idlib and Aleppo Governorates. The bad weather damaged 2,214 tents inhabited by 2,329 households in Atme, Sarmada, Deir Hassan, Al-Dana, and Al-Bab. In response, QRCS's representation mission i...


            **Your Task:**
            Write a 3–4 sentence impact assessment that:
            1. Grounds the prediction in the historical analogy
            2. Contextualizes the severity and scale of impact
            3. Highlights the key humanitarian and economic risks
            4. Uses precise, factual language suitable for a disaster response briefing

            Do NOT invent specific casualty numbers beyond what is provided. Do NOT speculate about causes.
```

### Expected Response *(Fill In)*

```

```

---

## Summary Statistics

- **Total Scenarios:** 50
- **Unique Disaster Types:** 19
- **Unique Countries:** 44
- **Scenarios With RAG Analogy:** 50
- **Scenarios Without Analogy:** 0
- **Avg Semantic Similarity (where found):** 0.6735
