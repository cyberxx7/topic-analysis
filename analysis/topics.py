"""
topics.py — Social Conflict Topic Dictionary

12 core topics tracked across Black media publications.
Each topic has a name, description, category color, and a rich set of
seed phrases used for matching article content.
"""

TOPICS = [
    {
        "id": "policing",
        "name": "Policing & Public Safety",
        "description": "Police reform, use of force, accountability, community safety, officer-involved shootings, qualified immunity",
        "color": "#C0392B",
        "seed_phrases": [
            "police brutality", "use of force", "officer involved shooting",
            "police accountability", "police reform", "qualified immunity",
            "defund the police", "community policing", "excessive force",
            "police misconduct", "law enforcement", "racial profiling",
            "stop and frisk", "chokehold", "body camera", "police violence",
            "civil rights violation", "unarmed black", "police killing",
            "police department", "sheriff", "blue wall of silence",
            "consent decree", "police union", "public safety",
            "no knock warrant", "swat team", "militarized police",
            "wrongful death", "excessive policing", "over-policing",
            "police officer", "officers disciplined", "officers charged",
            "officers fired", "officers acquitted", "won't be disciplined",
            "not disciplined", "officer misconduct", "officer fired",
            "cop killed", "cop shot", "shot by police", "killed by police",
            "arrested by police", "false arrest", "wrongful arrest",
            "fake gang", "gang database", "falsely charged", "falsely arrested",
            "ice agent", "immigration enforcement", "deportation raid",
            "federal agent", "homeland security"
        ]
    },
    {
        "id": "voter_suppression",
        "name": "Voter Suppression",
        "description": "Voting rights, ballot access restrictions, gerrymandering, election interference, disenfranchisement",
        "color": "#8E44AD",
        "seed_phrases": [
            "voter suppression", "voting rights", "voter id", "gerrymandering",
            "disenfranchisement", "ballot access", "election interference",
            "voter purge", "voting restriction", "poll tax", "voter intimidation",
            "election integrity", "voting law", "absentee ballot",
            "early voting", "voter registration", "redistricting",
            "precinct closure", "voting machine", "election security",
            "black voter", "minority voter", "voting access",
            "help america vote", "john lewis voting rights act",
            "shelby county", "section 5 preclearance", "felony disenfranchisement",
            "voters turned away", "disenfranchised", "democracy",
            "save america act", "save act", "civic engagement",
            "jim crow", "election law", "voters suppressed",
            "canvassing", "ballot harvesting", "voter rolls",
            "voters blocked", "polling place", "poll worker",
            "election day", "midterm", "primary election"
        ]
    },
    {
        "id": "book_bans_dei",
        "name": "Book Bans & Anti-DEI",
        "description": "Censorship of Black literature, DEI rollbacks, critical race theory bans, curriculum restrictions",
        "color": "#D35400",
        "seed_phrases": [
            "book ban", "banned book", "critical race theory", "crt",
            "diversity equity inclusion", "dei", "anti-dei",
            "curriculum censorship", "school board", "woke",
            "cultural erasure", "black history month", "1619 project",
            "ethnic studies", "inclusive curriculum", "black author",
            "censored book", "educational gag order", "don't say gay",
            "parental rights in education", "indoctrination",
            "cancel culture", "free speech campus", "academic freedom",
            "affirmative action ban", "diversity training",
            "equity program eliminated", "multicultural education"
        ]
    },
    {
        "id": "housing",
        "name": "Housing & Displacement",
        "description": "Affordable housing, eviction crisis, gentrification, homelessness, housing discrimination",
        "color": "#1A5276",
        "seed_phrases": [
            "affordable housing", "eviction", "gentrification", "displacement",
            "housing discrimination", "housing crisis", "rent burden",
            "homelessness", "housing insecurity", "public housing",
            "section 8", "housing voucher", "redlining", "mortgage discrimination",
            "fair housing", "landlord", "tenant rights", "rent control",
            "housing shortage", "housing cost", "shelter", "zoning",
            "urban renewal", "neighborhood change", "community land trust",
            "housing instability", "foreclosure", "predatory lending",
            "black homeownership", "housing segregation"
        ]
    },
    {
        "id": "maternal_health",
        "name": "Maternal Health",
        "description": "Black maternal mortality, obstetric racism, prenatal care disparities, childbirth outcomes",
        "color": "#117A65",
        "seed_phrases": [
            "maternal mortality", "maternal health", "black maternal",
            "obstetric racism", "prenatal care", "childbirth", "postpartum",
            "pregnancy complication", "infant mortality", "birth outcome",
            "midwife", "doula", "cesarean", "c-section",
            "maternal death", "maternal care", "birth equity",
            "reproductive health", "pregnancy care", "perinatal",
            "maternal morbidity", "unsafe childbirth", "pregnancy discrimination",
            "maternal mental health", "postpartum depression",
            "obstetric violence", "birth justice", "black birth"
        ]
    },
    {
        "id": "redlining",
        "name": "Redlining & Fair Housing",
        "description": "Historical redlining legacy, lending discrimination, neighborhood disinvestment, fair housing enforcement",
        "color": "#922B21",
        "seed_phrases": [
            "redlining", "fair housing act", "lending discrimination",
            "neighborhood disinvestment", "community reinvestment act",
            "racial wealth gap housing", "discriminatory appraisal",
            "home appraisal bias", "mortgage denial", "bank discrimination",
            "housing segregation history", "deed restriction",
            "racial covenant", "blockbusting", "white flight",
            "discriminatory zoning", "exclusionary zoning",
            "neighborhood segregation", "concentrated poverty",
            "disinvested community", "appraisal gap", "lending bias"
        ]
    },
    {
        "id": "surveillance",
        "name": "Anti-Black Surveillance",
        "description": "Mass surveillance, facial recognition bias, data privacy, government monitoring of Black communities",
        "color": "#1C2833",
        "seed_phrases": [
            "facial recognition", "surveillance", "data privacy",
            "predictive policing", "social media monitoring",
            "fusion center", "stingray", "cell site simulator",
            "license plate reader", "smart city surveillance",
            "algorithmic bias", "biometric data", "ring doorbell",
            "neighborhood watch racism", "gang database",
            "crime prediction algorithm", "digital redlining",
            "surveillance capitalism", "privacy rights", "spying",
            "fbi cointelpro", "government monitoring", "racial surveillance",
            "geofence warrant", "cell phone tracking"
        ]
    },
    {
        "id": "reparations",
        "name": "Reparations",
        "description": "Reparations for slavery, community investment, wealth redistribution, descendants of enslaved people",
        "color": "#784212",
        "seed_phrases": [
            "reparations", "slavery reparation", "hr 40",
            "commission to study reparation", "descendants of enslaved",
            "40 acres and a mule", "racial wealth gap repair",
            "atonement", "restorative justice", "repair the harm",
            "evanston reparations", "california reparations",
            "reparations program", "reparation payment",
            "acknowledgment of slavery", "truth and reconciliation",
            "anti-black atrocity", "racial injustice repair",
            "wealth redistribution", "community reparations"
        ]
    },
    {
        "id": "school_funding",
        "name": "School Funding",
        "description": "Education funding disparities, underfunded schools, school closures, Black student outcomes",
        "color": "#1A5276",
        "seed_phrases": [
            "school funding", "education funding", "school budget",
            "underfunded school", "school resource", "education disparity",
            "black student", "school closure", "school district",
            "title i", "per pupil spending", "property tax school funding",
            "education equity", "school quality", "teacher shortage",
            "school infrastructure", "learning gap", "achievement gap",
            "opportunity gap", "hbcu funding", "hbcu",
            "historically black college", "education access",
            "special education funding", "gifted program access",
            "degree program", "university", "college program",
            "FAMU", "Howard University", "Morehouse", "Spelman",
            "NCAA", "march madness hbcu", "student loan",
            "education cut", "department of education", "school choice",
            "charter school", "public school", "academic program"
        ]
    },
    {
        "id": "criminal_justice",
        "name": "Criminal Justice Reform",
        "description": "Mass incarceration, sentencing disparities, prison conditions, bail reform, reentry programs",
        "color": "#6C3483",
        "seed_phrases": [
            "mass incarceration", "criminal justice reform", "sentencing disparity",
            "mandatory minimum", "three strikes", "prison industrial complex",
            "cash bail", "bail reform", "pretrial detention",
            "wrongful conviction", "exoneration", "innocence project",
            "prison condition", "solitary confinement", "reentry",
            "recidivism", "probation", "parole", "juvenile justice",
            "school to prison pipeline", "felony disenfranchisement",
            "prosecutorial misconduct", "plea bargain", "public defender",
            "over-criminalization", "drug war", "crack cocaine disparity",
            "first step act", "second chance",
            "charged with murder", "charged with assault", "charged with",
            "indicted", "convicted", "sentenced to", "acquitted",
            "not guilty", "criminal charges", "facing charges",
            "arrested and charged", "prosecution", "criminal trial",
            "murder charge", "manslaughter", "assault charge",
            "abortion law charged", "charged under", "felony charge",
            "misdemeanor", "grand jury",
            "death sentence", "death row", "execution",
            "life sentence", "prison sentence", "buy prison",
            "second chance", "ex-inmate", "formerly incarcerated",
            "prison reform", "bail fund", "prison to pipeline",
            "supreme court criminal", "criminal appeal"
        ]
    },
    {
        "id": "environmental_justice",
        "name": "Environmental Justice",
        "description": "Environmental racism, pollution in Black communities, climate vulnerability, toxic exposure",
        "color": "#1E8449",
        "seed_phrases": [
            "environmental justice", "environmental racism",
            "pollution black community", "toxic waste", "superfund site",
            "clean air", "clean water", "water contamination",
            "lead poisoning", "flint water crisis", "cancer alley",
            "chemical plant", "refinery", "industrial facility",
            "climate change black community", "climate vulnerability",
            "heat island", "green space", "park access",
            "fossil fuel community", "sacrifice zone",
            "environmental health disparity", "asthma black children",
            "climate displacement", "flood risk", "hurricane recovery"
        ]
    },
    {
        "id": "economic_equity",
        "name": "Economic Equity & Wealth Gap",
        "description": "Racial wealth gap, Black entrepreneurship, wage discrimination, economic mobility, poverty",
        "color": "#B7950B",
        "seed_phrases": [
            "racial wealth gap", "economic equity", "wage gap",
            "pay discrimination", "black entrepreneur", "black business",
            "black-owned business", "economic mobility", "poverty",
            "financial inclusion", "banking access", "unbanked",
            "predatory lending", "payday loan", "credit access",
            "investment gap", "venture capital black founder",
            "economic disparity", "income inequality",
            "unemployment black", "job discrimination", "hiring bias",
            "glass ceiling", "black middle class", "economic empowerment",
            "generational wealth", "asset building", "financial literacy"
        ]
    }
]

# Build a lookup dict by topic id
TOPIC_LOOKUP = {t["id"]: t for t in TOPICS}

# All topic names for display
TOPIC_NAMES = [t["name"] for t in TOPICS]

# Color palette for charts
TOPIC_COLORS = {t["name"]: t["color"] for t in TOPICS}
