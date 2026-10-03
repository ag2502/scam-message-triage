"""English slot values and message templates for the synthetic corpus.

Templates are grouped by label. Each `{slot}` is filled from SLOTS (a list to
sample from, or a callable taking a `random.Random`). Rails, currencies, banks
and couriers are deliberately global so the model does not overfit to a single
country's payment system.
"""

from __future__ import annotations

import random
import string

NAMES = [
    "Ana", "João", "Priya", "Rahul", "Emily", "James", "Maria", "Carlos", "Fatima", "Wei", "Olivia", "Lucas",
    "Aisha", "David", "Sofia", "Mateus", "Ananya", "Michael", "Chloe", "Diego", "Grace", "Tom", "Juliana",
    "Arjun", "Sarah", "Kenji", "Isabela", "Daniel", "Zara", "Pedro", "Hannah", "Ravi", "Laura", "Sam",
]
RELATIONS = ["mum", "mom", "dad", "mam", "mother", "grandma", "nan", "auntie"]
KIDS = ["son", "daughter", "grandson", "granddaughter", "nephew", "niece"]
RAILS = ["Pix", "UPI", "Zelle", "bank transfer", "Venmo", "PayPal", "Cash App", "SPEI", "wire transfer", "Faster Payments"]
BANKS = [
    "Chase", "Wells Fargo", "Bank of America", "HSBC", "Barclays", "Lloyds", "Santander", "Monzo", "Nubank", "Itaú",
    "Banco Inter", "Bradesco", "SBI", "HDFC Bank", "ICICI Bank", "BBVA", "Citibank", "NatWest", "Revolut",
]
COURIERS = ["USPS", "DHL", "FedEx", "UPS", "Royal Mail", "Evri", "India Post", "Correios", "Canada Post", "DPD"]
SERVICES = ["Netflix", "Apple ID", "WhatsApp", "Instagram", "Microsoft", "PayPal", "Amazon", "Google", "Spotify", "Facebook"]
TOLLS = ["E-ZPass", "FasTrak", "SunPass", "Toll Services", "TxTag", "The Toll Roads"]
TAX_AUTHS = ["IRS", "HMRC", "Tax Department", "Revenue Service", "Income Tax Department"]
DMVS = ["DMV", "DVLA", "Department of Motor Vehicles", "Transport Authority"]
STORES = ["Amazon", "Walmart", "Tesco", "Target", "ASOS", "Mercado Livre", "Flipkart", "Shein", "IKEA", "Best Buy"]
MERCHANTS = ["Starbucks", "Uber", "Tesco", "Walmart", "Shell", "McDonald's", "Zara", "iFood", "Swiggy", "Lidl"]
CITIES = ["Lagos", "Moscow", "São Paulo", "Mumbai", "London", "Miami", "Manila", "Bucharest", "Jakarta"]
PLACES = ["airport", "train station", "hospital", "mall", "bus station", "police station", "pharmacy"]
ITEMS = ["sofa", "bike", "iPhone", "PS5", "fridge", "guitar", "laptop", "baby stroller", "concert tickets"]
COMPANIES = ["Amazon", "TikTok", "Hilton", "Booking", "Shopee", "Global Media", "Apex Digital", "Nova Marketing"]
GROUPS = ["school parents", "football", "neighbourhood", "family", "church", "book club", "work"]
CRYPTO = ["USDT", "Bitcoin", "BTC", "ETH", "crypto"]
EXCHANGES = ["CoinTradePro", "BitPrimeX", "Zentrix Exchange", "AlphaCoin Global", "MetaFX Trade"]
LOTTERIES = ["Mega Millions", "National Lottery", "Global Promo Draw", "Coca-Cola Promo", "WhatsApp Lottery"]
JOBS = ["nurse", "designer", "engineer", "fashion buyer", "doctor", "lawyer"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "tomorrow", "next week"]
MONTHS = ["January", "March", "May", "July", "September", "November"]
WALLET_APPS = ["Google Pay", "PhonePe", "Paytm", "Venmo", "Cash App", "PicPay", "Mercado Pago", "Revolut", "Monzo"]
UTILITIES = ["electricity", "water", "broadband", "gas", "phone"]
HOTELS = ["Ibis", "Hilton", "Airbnb", "Marriott", "Holiday Inn", "Booking.com"]
AIRLINES = ["LATAM", "British Airways", "IndiGo", "United", "Azul", "Ryanair"]
BANK_SITES = {
    "Chase": "chase.com", "Wells Fargo": "wellsfargo.com", "Bank of America": "bankofamerica.com", "HSBC": "hsbc.co.uk",
    "Barclays": "barclays.co.uk", "Lloyds": "lloydsbank.com", "Santander": "santander.com", "Monzo": "monzo.com",
    "Nubank": "nubank.com.br", "Itaú": "itau.com.br", "Banco Inter": "bancointer.com.br", "Bradesco": "bradesco.com.br",
    "SBI": "onlinesbi.sbi", "HDFC Bank": "hdfcbank.com", "ICICI Bank": "icicibank.com", "BBVA": "bbva.mx",
    "Citibank": "citi.com", "NatWest": "natwest.com", "Revolut": "revolut.com",
}
GOOD_URLS = [
    "https://www.amazon.com/your-orders", "https://www.usps.com/tracking", "https://www.royalmail.com/track",
    "https://www.dhl.com/track", "https://www.netflix.com/account", "https://www.gov.uk", "https://www.irs.gov",
    "amazon.com/your-orders", "fedex.com", "ups.com", "evri.com", "correios.com.br/rastreamento", "indiapost.gov.in",
    "https://www.booking.com/mytrips", "ikea.com/orders", "https://www.target.com/orders", "flipkart.com/account/orders",
]

_CURRENCIES = [("$", 1.0), ("£", 0.8), ("€", 0.9), ("R$", 5.0), ("₹", 80.0), ("MXN $", 18.0)]
_RISKY_TLDS = ["top", "xyz", "icu", "click", "live", "info", "shop", "buzz", "vip", "online", "cc"]
_LURE_WORDS = ["verify", "secure", "redelivery", "update", "pay", "track", "help", "support", "login", "claim", "refund"]


_message_currency: list[tuple[str, float]] = []


_message_bank: list[str] = []


def begin_message(rng: random.Random) -> None:
    """Called by the generator before each message so amounts share one currency and bank/site agree."""
    _message_currency[:] = [rng.choice(_CURRENCIES)]
    _message_bank[:] = [rng.choice(BANKS)]


def _amount(rng: random.Random, lo: float, hi: float) -> str:
    sym, rate = _message_currency[0] if _message_currency else rng.choice(_CURRENCIES)
    value = rng.uniform(lo, hi) * rate
    if value >= 100:
        value = round(value, -1) if rng.random() < 0.7 else round(value)
        s = f"{value:,.0f}"
    else:
        s = f"{value:.2f}"
    return f"{sym}{s}" if rng.random() < 0.9 else f"{s} {_currency_word(sym)}"


def _currency_word(sym: str) -> str:
    return {"$": "dollars", "£": "pounds", "€": "euros", "R$": "reais", "₹": "rupees", "MXN $": "pesos"}[sym]


def _bad_url(rng: random.Random) -> str:
    kind = rng.random()
    if kind < 0.2:
        host = rng.choice(["bit.ly", "tinyurl.com", "cutt.ly", "rb.gy", "is.gd"])
        return f"{host}/{''.join(rng.choices(string.ascii_letters + string.digits, k=6))}"
    if kind < 0.27:
        return f"http://{rng.randint(23, 223)}.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}/{rng.choice(_LURE_WORDS)}"
    brand = rng.choice(["usps", "dhl", "fedex", "royalmail", "paypal", "netflix", "apple", "amazon", "ezpass", "toll", "irs", "hmrc", "bank", "chase", "hsbc", "nubank", "gov"])
    host = f"{brand}-{rng.choice(_LURE_WORDS)}.{rng.choice(_RISKY_TLDS)}"
    if rng.random() < 0.3:
        host = f"{brand}.com.{rng.choice(_LURE_WORDS)}-{rng.choice(['acct', 'center', 'portal', 'id'])}.{rng.choice(['net', 'com', 'top'])}"
    scheme = rng.choice(["https://", "http://", ""])
    return f"{scheme}{host}/{rng.choice(['', 'i', 'pay', 'us', 'track', 'verify'])}".rstrip("/")


def _phone(rng: random.Random) -> str:
    d = lambda n: "".join(rng.choices(string.digits, k=n))  # noqa: E731
    return rng.choice([
        f"+1 ({d(3)}) {d(3)}-{d(4)}", f"+44 7{d(3)} {d(6)}", f"+55 {d(2)} 9{d(4)}-{d(4)}",
        f"+91 9{d(4)} {d(5)}", f"+52 {d(2)} {d(4)} {d(4)}", f"0800 {d(3)} {d(4)}", f"1-8{d(2)}-{d(3)}-{d(4)}",
    ])


def _pix_key(rng: random.Random) -> str:
    d = lambda n: "".join(rng.choices(string.digits, k=n))  # noqa: E731
    name = rng.choice(NAMES).lower().replace("ã", "a").replace("ç", "c")
    return rng.choice([f"{name}{d(3)}@gmail.com", f"+55 11 9{d(4)}-{d(4)}", f"{d(3)}.{d(3)}.{d(3)}-{d(2)}", f"{name}@upi", f"{name}{d(2)}@okbank"])


def _acct_details(rng: random.Random) -> str:
    d = lambda n: "".join(rng.choices(string.digits, k=n))  # noqa: E731
    name = f"{rng.choice(NAMES)} {rng.choice(['Silva', 'Smith', 'Kumar', 'Garcia', 'Okafor', 'Santos', 'Brown'])}"
    return rng.choice([
        f"{name}, sort code {d(2)}-{d(2)}-{d(2)}, account {d(8)}",
        f"{name}, account {d(10)}, routing {d(9)}",
        f"{name}, IBAN GB{d(2)} {d(4)} {d(4)} {d(4)} {d(4)}",
        f"{name}, Pix key {_pix_key(rng)}",
    ])


def _time(rng: random.Random) -> str:
    return f"{rng.randint(7, 11)}:{rng.choice(['00', '15', '30', '45'])}{rng.choice(['am', ''])}"


def _time2(rng: random.Random) -> str:
    return f"{rng.randint(12, 6 + 12) - 12 or 12}:{rng.choice(['00', '30'])}pm"


SLOTS: dict[str, object] = {
    "name": NAMES, "name2": NAMES, "kid_name": NAMES, "relation": RELATIONS, "kid": KIDS, "rail": RAILS,
    "bank": lambda r: _message_bank[0] if _message_bank else r.choice(BANKS),
    "bank_site": lambda r: BANK_SITES[_message_bank[0] if _message_bank else r.choice(BANKS)],
    "wallet_app": WALLET_APPS, "utility": UTILITIES, "hotel": HOTELS, "airline": AIRLINES, "courier": COURIERS, "service": SERVICES, "toll": TOLLS, "taxauth": TAX_AUTHS, "dmv": DMVS,
    "store": STORES, "merchant": MERCHANTS, "city": CITIES, "place": PLACES, "item": ITEMS, "company": COMPANIES,
    "group": GROUPS, "crypto": CRYPTO, "exchange": EXCHANGES, "lottery": LOTTERIES, "job": JOBS, "day": DAYS,
    "month": MONTHS, "good_url": GOOD_URLS,
    "relation_cap": lambda r: r.choice(RELATIONS).capitalize(),
    "amount": lambda r: _amount(r, 150, 2500),
    "amount2": lambda r: _amount(r, 2600, 6000),
    "small_amount": lambda r: _amount(r, 1.5, 60),
    "bad_url": _bad_url, "phone": _phone, "pix_key": _pix_key, "acct_details": _acct_details,
    "acct_name": lambda r: f"{r.choice(NAMES)} {r.choice(['Silva', 'Smith', 'Kumar', 'Garcia', 'Okafor'])}",
    "code": lambda r: "".join(r.choices(string.digits, k=6)),
    "last4": lambda r: "".join(r.choices(string.digits, k=4)),
    "txn": lambda r: "".join(r.choices(string.ascii_uppercase + string.digits, k=10)),
    "tracking": lambda r: r.choice(["US", "GB", "BR", "IN"]) + "".join(r.choices(string.digits, k=9)) + r.choice(["", "XX"]),
    "pct": lambda r: str(r.choice([15, 20, 30, 35, 40, 50, 80, 100, 150, 200, 300])),
    "handle": lambda r: f"{r.choice(NAMES).lower()}_{r.choice(['hr', 'jobs', 'recruit', 'team'])}{r.randint(1, 99)}",
    "wallet": lambda r: "T" + "".join(r.choices(string.ascii_letters + string.digits, k=33)),
    "date": lambda r: f"{r.randint(1, 28)} {r.choice(MONTHS)}",
    "year": lambda r: str(r.randint(2023, 2025)),
    "time1": _time, "time2": _time2,
    "flight": lambda r: r.choice(["BA", "LA", "AI", "UA", "AZ"]) + str(r.randint(100, 9999)),
    "gate": lambda r: r.choice("ABCD") + str(r.randint(1, 40)),
    "pharmacy": ["Boots", "CVS", "Walgreens", "Drogasil", "Apollo Pharmacy"],
    "broke": ["broke", "dropped", "lost", "smashed"],
    "order": lambda r: f"{r.randint(100, 999)}-{r.randint(1000000, 9999999)}",
    "points": lambda r: f"{r.randint(2, 90) * 100:,}",
    "pnr": lambda r: "".join(r.choices(string.ascii_uppercase + string.digits, k=6)),
    "device": ["iPhone", "Android phone", "Windows PC", "Mac", "iPad", "Chrome on Windows"],
}

TEMPLATES: dict[str, list[str]] = {
    "family_impersonation": [
        "Hi {relation}, this is my new number, I {broke} my phone. Can you save it and text me back?",
        "Hi {relation} it's me, my phone fell in the toilet so I'm using a temporary number. I need to pay a bill today and my banking app won't work on this phone. Can you help me out? I'll pay you back tomorrow",
        "{relation_cap} it's {kid_name}, new number. I'm in a bit of trouble and need {amount} urgently, can you send it via {rail}? I can't talk right now, will explain later",
        "Hey {relation}, lost my phone and this is my new number. Can you do me a favour and transfer {amount} to my friend's account? Details: {acct_details}. Please don't tell dad, I'll sort it out",
        "hi {relation} its me, phone broke, using a friends phone. need {amount} for rent its due today, can u {rail} it to this key {pix_key}",
        "Hello {relation}. I changed my number, delete the old one. Are you at home? I need a quick favour",
        "{relation_cap}, it's me. I'm stuck at the {place} and my card was declined. Please send {amount} to {acct_name} via {rail} right now, my mic isn't working so I can't call",
        "It's your {kid} here, this is my new number. I've got a payment that has to go out before 5pm and my online banking is locked for 24 hours. Could you pay it for me? It's {amount}",
        "Hi {relation}! Save my new number pls 🙏 the old one stopped working. Can you lend me {amount} until Friday? Urgent",
        "Hi grandma, it's your grandson. I got into a car accident and the police say I need {amount} for bail. Please don't tell mom and dad, send it by {rail} as soon as possible",
        "hey it's {kid_name}!! this is my new whatsapp, old phone got stolen 😩 can you send {amount} to cover my phone bill? I'll send it back when my bank sorts it",
        "Hi {relation}, I'm texting from a friend's phone, mine died. Can you send {amount} to this {rail} {pix_key}? It's for my train ticket, I'm stranded. Text only, can't call",
    ],
    "fake_payment_receipt": [
        "Hi, I accidentally sent {amount} to your {rail} instead of my sister's. Here is the receipt: {bad_url}. Could you please send it back? It's for my rent",
        "Good evening, sorry to bother you. I made a {rail} transfer of {amount} to you by mistake. Please return it to the key {pix_key}, I've attached the proof of payment",
        "{rail} payment received: {amount} from {name}. Status: PENDING. To release the funds, the recipient must send a confirmation fee of {small_amount}. Details: {bad_url}",
        "Hello, I paid for the {item} you listed but I sent too much by mistake, I paid {amount2} instead of {amount}. Please refund the difference to my {rail}. Screenshot attached",
        "Payment confirmation: {amount} has been sent to your account via {rail}. Transaction ID {txn}. The funds will be released once you return the overpayment of {small_amount}",
        "Sorry wrong number! I sent {amount} to you by accident, my son's number is almost the same. Can you send it back please? I'm a pensioner and I need it",
        "This is {name} from the marketplace. I've sent the money for the {item}, check the receipt {bad_url}. Our courier will pick it up today, please pay the {small_amount} shipping fee first and I'll refund it",
        "{rail} notice: Your account has been credited {amount}. To receive this payment you need to upgrade to a business account by sending {small_amount}",
        "hello I transferred {amount} into your account by mistake while paying my supplier, please kindly send back to {acct_details} today, bank says it takes 7 days to reverse",
        "Here is the receipt of the {rail} I sent you: {amount}. Please send back {small_amount} because I paid extra 🙏",
        "Hi I'm buying your {item}. I've made the payment of {amount}, the money is on hold until you send the tracking number and pay the {small_amount} insurance fee. See {bad_url}",
        "Dear customer, a {rail} of {amount} was made to your account in error. Kindly reverse the transaction within 24 hours to {acct_details} to avoid legal action",
    ],
    "bank_impersonation": [
        "{bank} Fraud Alert: A payment of {amount} to {name} was attempted from your account. If this wasn't you, call our fraud team immediately on {phone}",
        "{bank}: Suspicious activity detected on your account. Your card has been temporarily blocked. Reply YES to confirm it was you or call {phone} to unblock",
        "Hello, this is {name} from the {bank} security department. Your account has been compromised. To protect your savings we need you to move your money to a safe account we've set up for you",
        "{bank} Security: We've detected an unauthorised transaction of {amount}. To cancel it, please share the code we just sent to your phone with our agent",
        "Dear {bank} customer, your account will be suspended within 24 hours due to unusual login activity. Verify your identity here: {bad_url}",
        "Hi, it's {bank} fraud prevention. Your card was cloned. Please install AnyDesk so our technician can secure your account remotely",
        "{bank}: New device signed into your online banking from {city}. If this was NOT you, call {phone} immediately",
        "This is your bank's fraud team. Someone is trying to take a loan in your name. You must transfer your balance to a protected account today. Don't tell the branch staff, they may be involved",
        "{bank} alert: A {rail} transfer of {amount} is pending. If you did not authorise it, click {bad_url} to cancel",
        "URGENT from {bank}: your debit card ending {last4} is restricted. Confirm your card number and PIN at {bad_url} to restore access",
        "We have tried to reach you. This is {bank} customer protection. Please call back on {phone} about a suspicious payment, reference {txn}",
        "Good afternoon, I'm calling from {bank}. As discussed, read me the 6-digit code you received so I can block the fraudulent transfer",
        "{bank} investigations: staff at your branch are under investigation. Withdraw your savings in cash and a courier will collect them for safekeeping",
    ],
    "delivery_fee": [
        "{courier}: Your package could not be delivered due to an incomplete address. Update your details at {bad_url} within 24 hours",
        "{courier}: Your parcel is on hold. A redelivery fee of {small_amount} is required. Pay here: {bad_url}",
        "Your shipment {tracking} is held at customs. Pay the customs fee of {small_amount} to release it: {bad_url}",
        "We attempted to deliver your package today but no one was home. Reschedule your delivery: {bad_url}",
        "{courier} notice: your order is awaiting payment of shipping costs ({small_amount}). Failure to pay will result in return to sender. {bad_url}",
        "Hello, I'm the courier with your parcel from {store}. There's an unpaid delivery charge of {small_amount}, can you send it via {rail} so I can drop it off?",
        "Final notice: your {courier} parcel will be returned today. Confirm your address and pay {small_amount}: {bad_url}",
        "Your package delivery has been suspended due to an unpaid fee. Visit {bad_url} to complete payment",
        "{courier}: The item couldn't be delivered because the house number is missing. Reply Y, then reopen this message to activate the link {bad_url}",
        "Hi, parcel for you at our depot, tracking {tracking}. Small handling fee {small_amount} needed before tomorrow: {bad_url}",
        "Dear customer, your package is waiting for delivery. Please confirm your payment of {small_amount} through the following link: {bad_url}",
        "{courier} Express: incorrect postcode on your parcel. To avoid it being destroyed, update and pay a {small_amount} fee at {bad_url}",
    ],
    "toll_fine_tax": [
        "{toll}: You have an unpaid toll balance of {small_amount}. To avoid a late fee of {amount}, pay now at {bad_url}",
        "{taxauth}: You are eligible for a tax refund of {amount}. Claim it here before it expires: {bad_url}",
        "Final notice from {taxauth}: you owe back taxes. A warrant for your arrest will be issued unless you pay {amount} today. Call {phone}",
        "Traffic violation notice: your vehicle was recorded speeding. Pay the {small_amount} fine within 48 hours to avoid court action: {bad_url}",
        "{dmv}: Your driver's license will be suspended due to an outstanding parking penalty. Settle {small_amount} at {bad_url}",
        "This is the police department. There is a case registered against your ID. To avoid arrest, pay the security deposit of {amount} via {rail}",
        "Unpaid parking ticket. Reference {txn}. Pay {small_amount} now or the penalty doubles: {bad_url}",
        "{taxauth}: Your tax return has an error. Update your bank details to receive your refund: {bad_url}",
        "Government notice: your social security number has been suspended due to suspicious activity. Call {phone} immediately",
        "{toll}: Our records show your vehicle has unpaid tolls. Pay {small_amount} within 12 hours to avoid DMV penalties. {bad_url}",
        "Court summons: you missed jury duty. Pay the {amount} fine using gift cards to avoid a warrant. Call {phone}",
        "{dmv} reminder: your vehicle registration has an unpaid fee of {small_amount}. Your plate will be blocked. Pay at {bad_url}",
        "Customs department: a parcel in your name contains illegal items. To avoid a money laundering case you must verify your funds by transferring {amount} to the official account",
        "Your mobile number will be disconnected in 2 hours by the telecom authority due to illegal use. Press 9 or call {phone} to speak to the officer",
    ],
    "account_phishing": [
        "{service}: Your account has been suspended due to a billing problem. Update your payment details at {bad_url}",
        "Your {service} account has been locked because of unusual sign-in activity. Verify your identity: {bad_url}",
        "{service} Support: we couldn't process your last payment. Your membership will be cancelled today unless you update your card {bad_url}",
        "Security alert: someone tried to log in to your {service} account from {city}. Secure your account now: {bad_url}",
        "Your mailbox is full. Login at {bad_url} to verify your account or your emails will be deleted",
        "Dear user, your {service} ID will be deactivated within 24 hours. Confirm your password here {bad_url}",
        "{service}: Your subscription has expired. Renew now for only {small_amount}: {bad_url}",
        "Hi, this is {service} support. Your account will be disabled for violating our terms. Appeal here: {bad_url}",
        "Your {service} purchase of {amount} is being processed. If you did not make this order, call {phone} to cancel",
        "{service}: we detected a virus on your device. Call our technicians at {phone} to remove it",
        "Action required: confirm your {service} login details to keep your account active {bad_url}",
        "Your {service} payment of {amount} was declined. To avoid account closure please update billing information at {bad_url}",
    ],
    "verification_code_theft": [
        "Hi, sorry, I sent a 6-digit code to your number by mistake. Could you forward it to me please?",
        "Hey it's {name} from the {group} group, I'm trying to log in and the code went to your phone. Can you send it to me?",
        "Hello! You've been selected for the {store} giveaway. To confirm your entry, reply with the code you just received by SMS",
        "{service} support here. To verify your account, please tell us the code we sent you",
        "omg sorry wrong number, I put your number by accident, a code is going to come to you, can u send it pls",
        "Hi, I'm the admin of the {group} WhatsApp group. We are verifying all members. Please send me the code you'll receive now",
        "Hi {name}, I'm locked out of my account and I listed you as a trusted contact. You'll get a code, please share it with me",
        "This is {bank} security. A verification code has been sent to you, read it back to us to confirm the cancellation of the transaction",
        "Hey! Can you vote for my niece in a contest? You'll receive a code by SMS, just send it here 🙏",
        "Sorry to bother, I'm renewing my {service} and accidentally typed your number. Please forward the OTP",
        "Hello, I'm from {store} customer service. To process your refund please share the one-time password you receive",
        "Hi it's me, new number. I need to verify my WhatsApp and the code went to you, could you send it?",
    ],
    "prize_lottery": [
        "Congratulations! You have won {amount} in the {lottery}. To claim your prize, pay the processing fee of {small_amount} at {bad_url}",
        "You've been selected as the lucky winner of a free iPhone 17! Claim within 24 hours: {bad_url}",
        "{store} customer reward: you have been chosen to receive a {amount} gift card. Click {bad_url} to claim",
        "Your number won {amount} in our anniversary draw. Send your full name, bank details and a {small_amount} release fee to {phone}",
        "CONGRATS! You're our 1,000,000th visitor. Claim your reward now {bad_url}",
        "Dear winner, your email was selected in the international lottery. Prize: {amount}. Contact our agent on WhatsApp {phone}",
        "You have an unclaimed reward of {amount} expiring today. Redeem: {bad_url}",
        "{service} is giving away {amount} to celebrate our anniversary! You've been selected. Pay {small_amount} shipping to receive your gift",
        "Hi! You won our raffle 🎉 To receive the prize we need a small deposit of {small_amount} via {rail} for the delivery",
        "Final reminder: your prize of {amount} is waiting. A customs clearance fee of {small_amount} must be paid before release",
        "Your loyalty points worth {amount} will expire tonight. Exchange them for cash here: {bad_url}",
        "Congratulations, your phone number has won the {lottery} jackpot! Call {phone} with your winning code {code}",
    ],
    "job_task": [
        "Hi, I'm {name} from {company} recruitment. We have a part-time job: like YouTube videos and earn {small_amount}-{amount} per day. Interested?",
        "Work from home opportunity! Earn {amount} daily by completing simple online tasks. No experience needed. Reply YES",
        "Hello, your profile was recommended to us. Our company is hiring remote product reviewers, daily salary {amount}. Add me on Telegram: @{handle}",
        "Congratulations on completing your first tasks! To unlock your commission of {amount} you need to top up {small_amount} to your task account",
        "Your account balance is negative. Please recharge {amount} to continue the tasks and withdraw your earnings",
        "We are looking for people to rate hotels online. 30 minutes a day, earn {amount}. Contact {phone} on WhatsApp",
        "Hi, I'm a recruiter from {company}. Part-time position, pay {small_amount} per hour, just follow accounts on Instagram. Can I send details?",
        "To withdraw your {amount} earnings, you must pay a tax deposit of {small_amount} first. This will be refunded",
        "Hello! Are you interested in a flexible job? Earn up to {amount} per week by boosting app ratings. Message me for details",
        "Job offer: data entry from home, {amount}/week. A starter kit costs {small_amount}, payable via {rail}, refunded with your first salary",
        "You've been shortlisted for a remote assistant role. Please pay {small_amount} for the training materials to begin",
        "Earn extra income! Just like and share posts, {small_amount} per task, paid instantly to your {rail}. Join here {bad_url}",
        "Hi, our platform pays commission for every set of product orders you complete. Today you got a lucky order, top up {amount} to finish it and withdraw everything",
    ],
    "investment_crypto": [
        "Invest {small_amount} today and receive {amount} in 7 days, guaranteed profit with our AI trading bot",
        "Hi, I'm {name}, a crypto mentor. My students earn {pct}% weekly returns. Join my trading group: {bad_url}",
        "Double your money in 24 hours with our {crypto} mining pool. Risk-free. Minimum deposit {small_amount}",
        "Exclusive investment opportunity: {pct}% monthly returns, fully guaranteed. Spots are limited, reply now",
        "Your {crypto} wallet has accumulated {amount} in profits. Pay the withdrawal fee of {small_amount} to release them",
        "Hello dear, I made {amount} last month trading forex with my uncle's signals. I can show you how, just open an account at {bad_url}",
        "Celebrity-backed platform! Turn {small_amount} into {amount}. As seen on TV. Register at {bad_url}",
        "VIP trading signals: 98% accuracy, {pct}% daily profit. Send {small_amount} USDT to join",
        "Our fund pays a fixed {pct}% weekly. Refer friends for an extra bonus. Deposit via {rail}",
        "Your account on {exchange} is ready. To activate trading, deposit at least {small_amount} in {crypto} to wallet {wallet}",
        "Hi! Wrong number? Anyway, nice to meet you 😊 I'm a {job} who invests in gold futures, made {amount} this month. Want to learn?",
        "Government-approved investment scheme: earn {pct}% guaranteed returns. Limited time, act now {bad_url}",
    ],
    "legit": [
        # Real bank / service notifications (hard negatives: codes, amounts, banks)
        "{bank}: Your OTP for the transaction of {amount} is {code}. Do not share this code with anyone, including bank staff.",
        "{bank}: Your debit card ending {last4} was used for {amount} at {merchant} on {date}. If you don't recognise this, call the number on the back of your card.",
        "{service}: your verification code is {code}. It expires in 10 minutes. We will never call you to ask for it.",
        "{bank}: {amount} was credited to your account ending {last4} via {rail} from {name}.",
        "Reminder from {bank}: we will never ask you to move money to a safe account or share your PIN.",
        "Your {service} subscription renews on {date}. Manage it any time in the app.",
        "{bank}: Your statement for {month} is ready to view in the app.",
        "Your {rail} payment of {amount} to {name} was successful. Ref {txn}.",
        "{bank}: Your new card has been dispatched and should arrive within 5 working days.",
        "{bank}: You sent {amount} to {name} with {rail}. Ref {txn}. Questions? Visit {bank_site}",
        "{wallet_app}: you received {amount} from {name}.",
        "{wallet_app}: {name} paid you {small_amount}.",
        "{wallet_app}: payment of {small_amount} to {merchant} successful. Ref {txn}.",
        "{bank}: Pix received {amount} from {name}.",
        "{bank}: Payment of {amount} to {merchant} approved on your card ending {last4}.",
        "{bank}: Your salary of {amount} has been credited to your account ending {last4}.",
        "{bank}: Your {rail} transfer of {amount} to {name} is complete.",
        "{bank}: You've frozen your card ending {last4} in the app. You can unfreeze it any time.",
        "{bank}: We declined a payment of {amount} at {merchant}. If it was you, approve it in the app and try again.",
        "{bank}: Your payment of {amount} to {name} has been scheduled for {date}.",
        "{bank}: Your code to approve the {rail} of {amount} to {name} is {code}. Never share it. {bank} will never call to ask for it.",
        "{store}: Your order #{order} of {amount} is confirmed. We'll let you know when it ships.",
        "{store}: your refund of {small_amount} has been processed and will appear in 3-5 business days.",
        "{store} Rewards: you've earned {points} points. Your {small_amount} voucher is ready to use in store or online.",
        "Your {store} gift card balance is {small_amount}.",
        "{service}: a new sign-in to your account on a {device}. If this was you, you don't need to do anything.",
        "{service}: your payment of {small_amount} was successful. Thanks for subscribing.",
        "Your {service} free trial ends on {date}. You won't be charged if you cancel before then.",
        "Your {utility} bill of {amount} is ready and will be collected by direct debit on {date}.",
        "Hi {name}, your booking at {hotel} is confirmed for {date}. Total paid: {amount}.",
        "{airline}: your booking {pnr} is confirmed. Manage it in the {airline} app.",
        "{service}: your password was changed. If this wasn't you, open the app and go to Settings > Security.",
        "{bank}: Spotted something odd? Always check alerts in our official app. We never send links by text.",
        "Your {store} order of {amount} has been confirmed. View the details in the app.",
        "Thanks for your payment of {amount}. Your account is up to date.",
        # Real deliveries
        "{store}: Your order has shipped and will arrive {day}. Track it in your account on our app.",
        "{courier}: Your parcel will be delivered today between {time1} and {time2}. Your driver is {name}.",
        "Your package was delivered to your front door at {time1}. Thanks for shopping with {store}!",
        "{courier}: we missed you today. Your parcel is at the {place} pickup point, bring ID to collect it.",
        "Your package from {store} is out for delivery. Track: {good_url}",
        "Your {store} order #{order} has been delivered. View it at {good_url}",
        "{courier}: parcel {tracking} delivered and signed for by {name}.",
        "{courier}: track your parcel {tracking} at {good_url}",
        "{store}: your order is ready to collect from the store. Bring your order number {order}.",
        # Personal chat (hard negatives: money between people who know each other)
        "Hey {name}, running 10 min late, save me a seat!",
        "Mom can you send me {small_amount} for lunch? I'll pay you back on Friday ❤️",
        "Sent you {amount} on {rail} for the concert tickets, thanks for buying them!",
        "Hi {relation}, landed safely! Will call you when I get to the hotel.",
        "Can you pick up milk and bread on the way home?",
        "Happy birthday {name}!! 🎉 Hope you have an amazing day",
        "Just paid you back the {small_amount} for dinner via {rail} 👍",
        "Did you see the game last night? Unbelievable ending",
        "{name}, the rent this month is {amount}, I'll send my half by {rail} tomorrow",
        "Dad, my phone is at 5% so if I don't reply that's why. Home by 10",
        "Are we still on for coffee {day} at {time1}?",
        "Thanks for the lovely evening! Let's do it again soon",
        "Can you send me the photos from the trip when you get a chance?",
        "I'm at the pharmacy, do you need anything?",
        "Lost my phone yesterday, got a new one but same number. Let me know if you sent me anything!",
        "Hey, did you get my message about the weekend? Let me know if you can make it",
        "I accidentally deleted our chat, can you resend the address?",
        "Congratulations on the new job!! So proud of you 🎉",
        "Hey, I'll transfer you the {amount} for the trip tonight, what's your {rail} again?",
        "Hi {name}, it's {name2} from the gym, just checking you're still coming to the 6pm class?",
        "Hey {name}, I just sent the {amount} for the Airbnb, check your {rail}",
        "Got your {rail}, thanks! 🙌",
        "Can you {rail} me your share of dinner? It was {small_amount} each",
        "Hi {relation}, my train is delayed, I'll be home late. Don't wait up for dinner",
        "Hi {name}, I'm a recruiter at {company}. I came across your profile and think you'd be a great fit for a {job} role. Open to a call this week?",
        # Work, appointments, public services
        "Hi {name}, can we move our 1:1 to {day} afternoon? Something came up.",
        "Reminder: team meeting at {time1} in the main conference room.",
        "Hi {name}, thanks for applying to {company}. We'd like to schedule an interview. Are you free {day}?",
        "Your shift on {day} has been confirmed: {time1} to {time2}.",
        "Reminder: your appointment with Dr. {name} is on {day} at {time1}. Reply C to confirm or call the clinic to reschedule.",
        "Your table for 4 is booked for {day} at {time1}. See you then!",
        "Your flight {flight} is on time. Boarding starts at {time1}, gate {gate}.",
        "School notice: parents' evening is on {day} at {time1}. Please sign up at the front office.",
        "Your prescription is ready for collection at {pharmacy}.",
        "Your electricity bill of {amount} is due on {date}. Pay in the app or by your usual bank transfer.",
        "{store}: Get 20% off this weekend in store and online. Reply STOP to opt out.",
        "{taxauth}: Your tax return for {year} has been received and is being processed. No action is needed.",
        "The plumber is coming {day} between {time1} and {time2}, can you be home?",
        "Your car is due for its annual inspection by {date}. Book at your usual garage.",
    ],
}
