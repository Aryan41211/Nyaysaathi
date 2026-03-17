from __future__ import annotations

import re


class HinglishNormalizer:
    # Group 1 - Spelling fixes
    _spell_map = {
        "huii": "hui",
        "gya": "gaya",
        "nhi": "nahi",
        "h": "hai",
        "kr": "kar",
        "pr": "par",
        "aj": "aaj",
        "rha": "raha",
        "gyi": "gayi",
        "gye": "gaye",
        "aya": "aaya",
        "kro": "karo",
        "abhi tak": "until now",
        "kai mahine": "several months",
        "teen mahine": "three months",
        "do mahine": "two months",
        "ek saal": "one year",
        "kai din": "several days",
        "3 mahine": "three months",
        "2 mahine": "two months",
        "three months se": "three months",
        "two months se": "two months",
    }

    # Group 2 - Crime and police
    _crime_police_map = {
        "ghar mein chori": "house robbery domestic",
        "ghar pe chori": "house robbery domestic",
        "ghar par chori": "house robbery domestic",
        "aaj chori hui": "theft at home today",
        "ghar toota": "house break in domestic robbery",
        "mere ghar par aaj chori hui": "house robbery police fir theft occurred",
        "mere ghar par chori hui": "house robbery police fir theft occurred",
        "ghar par chori hui": "house robbery police fir theft occurred",
        "chori hui": "theft occurred",
        "chori ho gayi": "theft occurred",
        "mera mobile chori": "mobile stolen",
        "meri gaadi chori": "vehicle stolen",
        "ghar mein chori": "house robbery",
        "ghar toota": "house break in",
        "mujhe loota": "i was robbed",
        "maar diya": "physically assaulted",
        "mujhe mara": "i was beaten",
        "pitai ki": "physical assault",
        "maar peet": "physical assault",
        "dhamki di": "threat given",
        "jaan se maarne ki dhamki": "death threat",
        "blackmail kar raha": "blackmail",
        "hafta maang raha": "extortion",
        "rangdaari": "extortion",
        "kidnap kar liya": "kidnapping",
        "pakad ke le gaye": "kidnapping",
        "police ne nahi suna": "police refused fir",
        "fir nahi likhi": "police refused fir",
        "thane gaya par kuch nahi hua": "police refused fir",
        "police ne bhaga diya": "police refused fir",
        "police ne maara": "police brutality",
        "thane mein maara": "custodial torture",
        "police bribe maang rahi": "police corruption",
        "nasha bik raha": "drug sale",
        "sharab bik rahi": "illegal liquor",
        "satta chal raha": "illegal gambling",
        "hatya": "murder complaint",
        "khoon": "murder complaint",
    }

    # Group 3 - Property
    _property_map = {
        "zameen": "land",
        "khet": "agricultural land",
        "kabza kar liya": "illegal encroachment",
        "kabza ho gaya": "encroachment",
        "seema vivad": "boundary dispute",
        "hadd ka jhagda": "boundary dispute",
        "zameen chheen li": "land grabbed",
        "registry nahi ki": "property not registered",
        "mutation nahi hua": "land mutation pending",
        "dakhil kharij": "land mutation",
        "wirasat": "inheritance",
        "pitaji ki zameen": "ancestral property",
        "property ka batwara": "property division",
        "hissa nahi diya": "property share denied",
        "girvee": "mortgage",
        "nakli kagaz": "fake documents",
        "farzi kagaz": "forged documents",
        "builder ne dhoka diya": "builder fraud",
        "flat nahi diya": "flat not given",
        "possession nahi diya": "possession not given",
    }

    # Group 4 - Labour
    _labour_map = {
        "three months se": "three months",
        "two months se": "two months",
        "salary nahi di": "salary not paid",
        "salary nahi mili": "salary not paid",
        "mazdoori nahi di": "wages not paid",
        "thekedar ne paisa nahi diya": "contractor wages not paid",
        "naukri se nikala": "wrongful termination",
        "bina notice ke nikala": "terminated without notice",
        "pf nahi mila": "provident fund denied",
        "gratuity nahi mili": "gratuity denied",
        "overtime nahi diya": "overtime not paid",
        "maternity leave nahi di": "maternity benefit denied",
        "kaam par chot lagi": "workplace accident",
        "bandhua mazdoor": "bonded labour",
        "bachche se kaam": "child labour",
        "boss ne galat harkat ki": "workplace sexual harassment",
    }

    # Group 5 - Family and domestic
    _family_map = {
        "pati roz maarta hai dahej ke liye": "dowry harassment domestic violence",
        "pati maarta hai dahej ke liye": "dowry harassment domestic violence",
        "pati ne mara": "domestic violence",
        "pati maarta hai": "husband beats me",
        "maarta hai": "beats",
        "sasural wale marte hain": "in law violence",
        "dahej maang rahe": "dowry harassment",
        "dahej ke liye maar rahe": "dowry harassment",
        "talaq": "divorce",
        "bacche nahi de raha": "child custody dispute",
        "guzara bhatta nahi de raha": "maintenance not paid",
        "pati chhod gaya": "husband deserted",
        "jabardasti shaadi": "forced marriage",
        "naabalig ki shaadi": "child marriage",
        "jaan ka khatra ghar walo se": "honour killing threat",
        "zewar wapas nahi diya": "streedhan not returned",
    }

    # Group 6 - Fraud and cyber
    _fraud_cyber_map = {
        "upi se paisa gaya": "upi payment fraud",
        "saamaan nahi mila": "product not delivered",
        "samaan nahi mila": "product not delivered",
        "paisa gaya online": "online fraud",
        "otp diya aur paisa gaya": "otp scam",
        "otp maanga": "otp fraud",
        "bank se paisa gaya": "banking fraud",
        "upi fraud": "upi payment fraud",
        "online thagi": "online fraud",
        "fake call aaya": "vishing scam",
        "lottery jeeta": "lottery fraud",
        "naukri ke naam pe paisa liya": "job fraud",
        "shaadi site pe dhoka": "matrimonial fraud",
        "qr code scan kiya": "qr code scam",
        "whatsapp pe maanga": "whatsapp fraud",
        "deepfake": "deepfake blackmail",
        "investment fraud": "investment fraud",
        "share market fraud": "stock market fraud",
    }

    # Group 7 - Tenant and rent
    _tenant_rent_map = {
        "kiraya nahi de raha": "tenant not paying rent",
        "deposit wapas nahi": "security deposit not returned",
        "ghar se nikaala": "illegal eviction",
        "bijli band ki": "utilities cut",
        "maalik bina bataaye aaya": "landlord unauthorized entry",
        "ghar kharab hai": "uninhabitable accommodation",
        "kiraya badha diya": "illegal rent hike",
        "maalik ke aadmi aaye": "landlord harassment goons",
    }

    # Group 8 - Government schemes
    _govt_map = {
        "ration nahi mila": "ration pds not given",
        "pension nahi aayi": "pension not received",
        "pension ruk gayi": "pension stopped",
        "certificate nahi bana": "certificate not issued",
        "jaati praman patra": "caste certificate",
        "scholarship nahi mili": "scholarship not paid",
        "pm awas nahi mila": "housing scheme complaint",
        "mnrega kaam nahi mila": "nrega work not given",
        "rishwat maangi": "bribery complaint",
        "sarkari babu ne paisa maanga": "government official bribery",
        "passport nahi bana": "passport delay",
        "aadhaar update nahi": "aadhaar update refused",
    }

    # Group 9 - Consumer
    _consumer_map = {
        "naya product kharab": "defective product",
        "warranty nahi mani": "warranty denied",
        "insurance claim nahi diya": "insurance claim rejected",
        "bijli bill bahut zyada": "electricity overcharging",
        "hospital ne zyada paisa liya": "hospital overcharging",
        "doctor ne galti ki": "medical negligence",
        "dawaai se nuksan hua": "medicine defective",
        "online course fraud": "education platform fraud",
        "builder ne amenities nahi di": "builder amenities complaint",
        "beej kharab nikle": "defective seeds",
    }

    # Group 10 - Senior citizen
    _senior_map = {
        "bujurg ko nikaala": "senior citizen eviction",
        "beta nahi dekh raha": "children not maintaining parents",
        "bujurg ka paisa le liya": "financial exploitation elderly",
        "pension nahi de rahe": "pension denied senior",
        "nursing home mein bura haal": "old age home complaint",
        "bujurg ko band kar rakha": "wrongful confinement elderly",
    }

    _map = {
        **_crime_police_map,
        **_property_map,
        **_labour_map,
        **_family_map,
        **_fraud_cyber_map,
        **_tenant_rent_map,
        **_govt_map,
        **_consumer_map,
        **_senior_map,
    }

    _space_re = re.compile(r"\s+")

    def normalize(self, text: str) -> str:
        # 1) Lowercase input
        value = str(text or "").lower().strip()
        value = self._space_re.sub(" ", value)

        # 2) Fix spellings (longest match first)
        for wrong, right in sorted(self._spell_map.items(), key=lambda pair: len(pair[0]), reverse=True):
            value = re.sub(rf"\b{re.escape(wrong)}\b", right, value)

        # 3) Replace mapped phrases (longest match first)
        ordered_mappings = sorted(self._map.items(), key=lambda pair: len(pair[0]), reverse=True)
        for _ in range(2):
            for source, target in ordered_mappings:
                value = re.sub(rf"\b{re.escape(source)}\b", target, value)

        # 4) Return cleaned English text
        value = self._space_re.sub(" ", value).strip()
        return value
