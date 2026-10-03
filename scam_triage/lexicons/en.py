"""English lexicon: regex patterns per signal plus the plain-language reason shown to users.

Patterns are matched case-insensitively against normalized text. Keep them
rail-agnostic: name every payment rail people actually use (Pix, UPI, Zelle...)
rather than tuning to one country.
"""

PATTERNS: dict[str, list[str]] = {
    "urgency": [
        r"\burgent(ly)?\b", r"\bimmediately\b", r"\bright now\b", r"\basap\b",
        r"\bwithin \d+ ?(hours?|hrs?|minutes?|mins?)\b", r"\blast chance\b",
        r"\bfinal (notice|warning|reminder)\b", r"\bexpires? (today|soon|tonight)\b",
        r"\bact now\b", r"\bas soon as possible\b", r"\bbefore (it'?s too late|midnight|5 ?pm)\b",
        r"\bquick(ly)?\b.{0,20}\bplease\b", r"\btoday only\b",
    ],
    "money_request": [
        r"\b(send|transfer|lend|pay|wire)\b.{0,25}\b(me|money|it|the (amount|balance|fee)|now)\b",
        r"\bcan you (send|transfer|lend|pay|help me with)\b",
        r"\bi need (money|cash|\$|£|€|r\$|₹|\d)", r"\bneed to pay\b",
        r"\bpay (the|a|this|your) (fee|fine|toll|balance|amount|charge)\b",
        r"\b(make|complete) (a|the) (payment|deposit|transfer)\b",
    ],
    "payment_rail": [
        r"\bpix\b", r"\bpix key\b", r"\bupi\b", r"\bupi id\b", r"\bzelle\b", r"\bvenmo\b",
        r"\bcash ?app\b", r"\bpaypal\b", r"\bspei\b", r"\bbre-?b\b", r"\bbank transfer\b",
        r"\bwire transfer\b", r"\bfaster payments?\b", r"\bsort code\b", r"\biban\b",
        r"\baccount number\b", r"\brouting number\b", r"\bgift ?cards?\b", r"\bitunes card\b",
        r"\bsteam card\b", r"\bbitcoin\b", r"\bbtc\b", r"\busdt\b", r"\bcrypto ?wallet\b",
        r"\bwestern union\b", r"\bmoneygram\b",
    ],
    "new_number": [
        r"\bnew number\b", r"\bchanged my number\b", r"\b(lost|broke|dropped|smashed) my phone\b",
        r"\bthis is my new\b", r"\bsave (this|my new) number\b", r"\bdelete (the|my) old number\b",
        r"\bphone (is )?(broken|died|got stolen)\b", r"\btemporary (number|phone)\b",
    ],
    "family_claim": [
        r"\bhi (mum|mom|mam|dad|mother|father|grandma|grandpa|nan|auntie|uncle)\b",
        r"\b(hello|hey) (mum|mom|dad)\b", r"\bit'?s (me|your) (son|daughter|grandson|granddaughter|nephew|niece)\b",
        r"\byour (son|daughter|grandson|granddaughter)\b", r"\bit'?s me,? (mum|mom|dad)\b",
    ],
    "secrecy": [
        r"\bdon'?t tell\b", r"\bkeep (this|it) (between us|secret|quiet)\b", r"\bdon'?t (mention|say anything)\b",
        r"\bnobody (else )?(can|should) know\b", r"\bdo not discuss this with\b",
    ],
    "avoid_voice": [
        r"\bcan'?t (call|talk|speak)\b", r"\b(mic|microphone|speaker) (is )?(broken|not working)\b",
        r"\bdon'?t call\b", r"\btext (me )?only\b", r"\bcan'?t take calls\b",
    ],
    "code_request": [
        r"\b(send|share|forward|tell|give|read)\b.{0,40}\b(code|otp|pin|passcode)\b",
        r"\b(code|otp)\b.{0,30}\b(by mistake|by accident|accidentally|wrong number)\b",
        r"\b\d-?digit code\b.{0,40}\b(send|share|forward|reply)\b",
        r"\breply with (the|your) (code|otp|pin)\b",
        r"\b(code|otp)\b.{0,60}\b(send|forward|share|give)\b (it|that|them)\b",
        r"\bwhat'?s the (code|otp)\b", r"\b(code|otp) (that )?(you )?(just )?(got|received)\b",
        r"\b(code|otp) (goes|went|will go|is going|will come|is coming) to (you|your)\b",
    ],
    "credential_request": [
        r"\b(enter|confirm|verify|update|provide|send)\b.{0,30}\b(password|card number|cvv|cvc|pin|login|security questions?|card details|bank details)\b",
        r"\bfull card (number|details)\b",
    ],
    "account_threat": [
        r"\b(account|card|access|profile)\b.{0,30}\b(suspended|locked|blocked|deactivated|disabled|restricted|frozen|on hold|closed)\b",
        r"\bunusual (activity|sign-?in|login)\b", r"\bsuspicious (activity|transaction|login|payment)\b",
        r"\bwill be (closed|suspended|deleted|terminated|blocked)\b", r"\bunauthori[sz]ed (transaction|payment|access)\b",
    ],
    "safe_account": [
        r"\bsafe account\b", r"\bsecure account\b", r"\bprotected account\b", r"\bholding account\b",
        r"\bmove (your|the|all) (money|funds|savings|balance)\b", r"\btransfer (your|all) (funds|savings|money|balance) to\b",
        r"\bbuy gold\b", r"\bcourier will collect\b", r"\bkeep (them|it|your (money|savings|funds)) safe\b",
        r"\bwithdraw (your|all) (savings|cash|money)\b",
    ],
    "remote_access": [
        r"\banydesk\b", r"\bteamviewer\b", r"\bquick ?support\b", r"\brustdesk\b",
        r"\bscreen ?shar(e|ing)\b", r"\bremote (access|support) app\b", r"\binstall (this|the) app\b",
    ],
    "refund_mistake": [
        r"\bby (mistake|accident)\b", r"\baccidentally (sent|transferred|paid)\b",
        r"\b(sent|transferred|paid) (it )?to the wrong (number|account|person)\b",
        r"\b(return|refund|send back|give back) the (money|amount|payment|difference|extra)\b",
        r"\boverpa(id|yment)\b",
    ],
    "prize": [
        r"\bcongratulations\b", r"\byou (have |'ve )?(won|been selected|been chosen)\b", r"\bwinner\b",
        r"\bprize\b", r"\bgiveaway\b", r"\blucky (draw|customer|winner)\b", r"\bclaim (your|the) (reward|prize|gift)\b",
        r"\bfree (iphone|gift|voucher)\b",
    ],
    "fee_to_unlock": [
        r"\b(small|processing|handling|release|customs|redelivery|delivery|clearance|activation|unlock|withdrawal|shipping) fee\b",
        r"\bpay (a|the) fee\b", r"\b(deposit|top up|recharge)\b.{0,30}\b(unlock|withdraw|release|continue|activate)\b",
        r"\bto (unlock|release|withdraw) (your|the) (funds|earnings|commission|prize|money)\b",
        r"\bwithdraw\b.{0,40}\b(recharge|deposit|top up)\b", r"\bpay\b[^.]{0,20}\b(gst|duty|registration charges?)\b",
    ],
    "easy_income": [
        r"\bwork from home\b", r"\bearn (up to )?(\$|£|€|r\$|₹)?\d", r"\bper (day|hour)\b.{0,20}\b(earn|income|salary|pay)\b",
        r"\b(daily|weekly) (income|salary|earnings|commission)\b", r"\b(like|rate|review) (videos|products|hotels|posts)\b",
        r"\bsimple (online )?tasks?\b", r"\bpart[- ]time (job|position|work)\b.{0,40}\b(earn|\$|£|€|₹)",
        r"\bno experience (needed|required)\b", r"\bcommission\b", r"\b(combo|merge|lucky) (task|order)s?\b",
        r"\b(boost|increase) (app )?(downloads|ratings|sales)\b",
    ],
    "guaranteed_return": [
        r"\bguaranteed\b.{0,30}\b(profit|returns?|income)\b", r"\bdouble your\b", r"\brisk[- ]free\b",
        r"\b\d{1,4}(\.\d+)? ?% (daily|weekly|monthly|profit|returns?)\b",
        r"\bsend\b.{0,30}\b(receive|get)\b.{0,25}\b(back|double)\b", r"\b(daily|weekly) (profit|returns?)\b",
        r"\bx\d{1,3} (your )?(money|investment)\b", r"\btrading (signals?|mentor|group|platform)\b",
        r"\binvest(ment)? opportunity\b",
    ],
    "authority": [
        r"\birs\b", r"\bhmrc\b", r"\btax (office|refund|authority|department|return)\b", r"\bunpaid (toll|fine|tax|ticket)\b",
        r"\btoll (services?|road|charges?|balance)\b", r"\be-?z ?pass\b", r"\bfastrak\b", r"\bsunpass\b", r"\bdmv\b",
        r"\btraffic (fine|violation|ticket)\b", r"\bparking (fine|ticket|penalty)\b", r"\bcourt\b", r"\bpolice\b",
        r"\barrest warrant\b", r"\bpenalty\b", r"\bgovernment\b", r"\bsocial security\b",
        r"\bdigital arrest\b", r"\bmoney laundering\b", r"\bcbi\b", r"\bcustoms (officer|department)\b",
        r"\bnarcotics\b", r"\bcyber (cell|crime)\b",
    ],
    "delivery": [
        r"\b(parcel|package|shipment|delivery|courier)\b", r"\busps\b", r"\bdhl\b", r"\bfedex\b", r"\bups\b",
        r"\broyal mail\b", r"\bevri\b", r"\bindia post\b", r"\bcorreios\b", r"\btracking (number|id)\b",
    ],
    "bank_mention": [
        r"\bbank\b", r"\bfraud (department|team|prevention|alert)\b", r"\bsecurity (team|department)\b",
        r"\b(debit|credit) card\b", r"\bvisa\b", r"\bmastercard\b",
    ],
}

REASONS: dict[str, str] = {
    "urgency": "Pressures you to act fast. Scammers rush you so you don't stop to check.",
    "money_request": "Asks you to send or pay money.",
    "payment_rail": "Mentions an instant or hard-to-reverse payment method (e.g. Pix, UPI, Zelle, gift cards, crypto).",
    "new_number": "Claims to be someone you know writing from a new or temporary number.",
    "family_claim": "Claims to be a family member without any way to verify it.",
    "secrecy": "Asks you to keep it secret. Real family and real banks don't do this.",
    "avoid_voice": "Avoids a voice call, so you can't recognise who it really is.",
    "code_request": "Asks you to share a verification/one-time code, which gives them access to your account.",
    "credential_request": "Asks for passwords, card details or other credentials.",
    "account_threat": "Threatens that an account or card is blocked or at risk.",
    "safe_account": "Asks you to move money to a 'safe account'. Banks never ask this.",
    "remote_access": "Asks you to install a screen-sharing or remote-access app.",
    "refund_mistake": "Claims money was sent by mistake and asks for it back.",
    "prize": "Says you won a prize or were 'selected'.",
    "fee_to_unlock": "Asks for a fee or deposit before you can receive something.",
    "easy_income": "Promises easy money for little work.",
    "guaranteed_return": "Promises guaranteed or unrealistically high returns.",
    "authority": "Claims to be a government, tax, toll or police authority.",
    "delivery": "Talks about a parcel or delivery.",
    "bank_mention": "Claims to be from a bank or its fraud team.",
    "has_link": "Contains a link.",
    "suspicious_link": "The link looks suspicious (shortened, unusual domain or imitating a brand).",
    "has_phone_number": "Asks you to contact a phone number given in the message.",
    "money_amount": "Mentions a specific amount of money.",
}

# Brands commonly imitated in look-alike domains (e.g. "usps-redelivery.top").
IMITATED_BRANDS: list[str] = [
    "usps", "dhl", "fedex", "ups", "royalmail", "evri", "amazon", "paypal", "apple", "icloud", "netflix",
    "whatsapp", "meta", "facebook", "instagram", "microsoft", "outlook", "google", "chase", "wellsfargo",
    "bankofamerica", "hsbc", "barclays", "santander", "nubank", "itau", "bradesco", "inter", "sbi", "hdfc",
    "icici", "irs", "hmrc", "ezpass", "toll", "dmv", "gov", "bank", "secure", "verify", "login",
]
