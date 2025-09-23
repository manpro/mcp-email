// User Profile Configuration
// Detta används av AI för att förstå vad som är viktigt för dig

export const userProfile = {
  name: "Mikael",

  newsPreferences: {
    // Intresseområden rankat efter prioritet
    highPriority: [
      "Svenska lokala nyheter",
      "EU-nyheter som påverkar Sverige",
      "Ukraina-konflikten",
      "Israel-Palestina konflikten",
      "Makroekonomiska nyheter",
      "Stora företag med bred påverkan (FAANG, svenska storbolag)",
      "Centralbanker och räntebesked",
      "Svensk politik och policy"
    ],

    mediumPriority: [
      "Nordiska nyheter",
      "EU-politik och regleringar",
      "Fintech och betalningslösningar",
      "Tech-industrin generellt",
      "Energimarknaden"
    ],

    lowPriority: [
      "Sport (förutom barnens aktiviteter)",
      "Underhållning",
      "Lokala nyheter Asien",
      "Lokala nyheter USA"
    ],

    spam: [
      "Kryptovaluta-pump schemes",
      "Penny stocks",
      "Get-rich-quick",
      "Lokala erbjudanden utanför Sverige"
    ]
  },

  personalInterests: {
    family: {
      priority: "critical",
      keywords: ["fotboll", "träning", "skola", "föräldramöte"],
      actions: ["add_to_calendar", "mark_important"]
    },

    finance: {
      priority: "high",
      mustInclude: ["makro", "centralbank", "ränta", "inflation", "BNP"],
      companies: ["Apple", "Microsoft", "Google", "Amazon", "Tesla", "Investor", "H&M", "Volvo", "Ericsson"],
      regions: ["Sverige", "EU", "USA", "Global"]
    },

    geopolitics: {
      priority: "high",
      regions: ["Ukraina", "Ryssland", "Israel", "Palestina", "Gaza", "NATO", "EU"],
      topics: ["konflikt", "sanktioner", "diplomati", "militär", "humanitär"]
    }
  },

  emailRules: {
    autoArchive: [
      "nyhetsbrev som är över 3 dagar gamla",
      "kvitton som är över 30 dagar",
      "marknadsföring som inte matchar intressen"
    ],

    autoFlag: [
      "fakturor",
      "betalningspåminnelser",
      "viktiga datum",
      "barnens aktiviteter"
    ],

    customFolders: {
      "Nyheter/Sverige": ["svenska nyheter", "lokalt sverige", "svensk politik"],
      "Nyheter/Ekonomi": ["makroekonomi", "centralbank", "börs", "finans"],
      "Nyheter/Geopolitik": ["ukraina", "israel", "nato", "eu politik"],
      "Familj/Fotboll": ["fotbollsträning", "match", "cup"],
      "Familj/Skola": ["skola", "utvecklingssamtal", "föräldramöte"],
      "Ekonomi/Fakturor": ["faktura", "invoice", "betalning"],
      "Arbete": ["izettle", "paypal", "jobb", "möte"]
    }
  },

  aiInstructions: `
När du analyserar emails, tänk på följande:

1. PRIORITERA HÖGT:
   - Svenska lokala nyheter och EU-nyheter som påverkar Sverige
   - Ukraina/Ryssland-konflikten och Israel/Palestina-situationen
   - Makroekonomiska nyheter (särskilt räntor, inflation, centralbanker)
   - Stora företag med bred marknadspåverkan
   - Allt relaterat till barnens aktiviteter (fotboll, skola)

2. FILTRERA BORT:
   - Lokala nyheter från Asien och USA (om de inte har global påverkan)
   - Mikroekonomi som inte påverkar makro
   - Små företagsnyheter utan bredare betydelse
   - Generisk marknadsföring

3. SMART KATEGORISERING:
   - Om en finansnyhet handlar om ett stort företag ELLER makroekonomi = VIKTIGT
   - Om en geopolitisk nyhet handlar om Ukraina/Israel = VIKTIGT
   - Om det är svenskt/nordiskt/EU och lokalt = VIKTIGT
   - Barnens aktiviteter = ALLTID KRITISKT

4. FÖRESLAGNA ÅTGÄRDER:
   - Fotbollsträning → Lägg till i kalender
   - Faktura → Flagga och påminn om förfallodatum
   - Viktiga nyheter → Sammanfatta kort på svenska
   - Spam/ointressant → Föreslå avprenumeration
`
}

export const getAIPromptForEmail = (email) => {
  return `
Analysera detta email baserat på Mikaels profil:

Email från: ${email.from}
Ämne: ${email.subject}
Innehåll: ${email.text?.slice(0, 500)}

Användarens intressen:
- Prioriterar: Svenska/EU nyheter, Ukraina/Israel, makroekonomi, barnaktiviteter
- Ignorerar: Lokala Asien/USA nyheter, mikroekonomi utan makropåverkan

Returnera JSON med:
- priority: critical/high/normal/low
- category: news_sweden/news_economy/news_geopolitics/family/invoice/spam/other
- suggestedFolder: Mapp enligt reglerna
- action: unsubscribe/archive/flag/add_to_calendar/none
- reason: Kort förklaring på svenska
`
}