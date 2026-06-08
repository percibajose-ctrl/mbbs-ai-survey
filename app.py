import streamlit as st
import google.generativeai as genai
import requests, json, uuid
from datetime import datetime

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
MODEL = genai.GenerativeModel("gemini-1.5-flash")
APPSCRIPT_URL = st.secrets["https://script.google.com/macros/s/AKfycbwTnJ-G_PC6EzaznnJ-cs2YFX5h-WG2BuDKL8kCcX7wQdi2OoTyB6eK_XnoPIjtjiI/exec"]

TOPICS = {
    "1st Year": {
        "Anatomy": ["Brachial plexus","Inguinal canal","Femoral triangle","Cubital fossa","Cavernous sinus"],
        "Physiology": ["Cardiac cycle","Action potential","Renal clearance","ECG basics","Reflex arc"],
        "Biochemistry": ["Glycolysis","Krebs cycle","Urea cycle","Hemoglobin","DNA replication"],
    },
    "2nd Year": {
        "Pathology": ["Inflammation","Neoplasia","Atherosclerosis","Granuloma","Apoptosis"],
        "Pharmacology": ["Antihypertensives","Antibiotics","NSAIDs","Insulin","Anticoagulants"],
        "Microbiology": ["Tuberculosis","HIV","Malaria","Staphylococcus","Hepatitis viruses"],
        "Forensic Medicine": ["Asphyxia","Postmortem changes","Poisoning","Injuries","Identification"],
    },
    "3rd Year Part 1": {
        "Community Medicine": ["Epidemiology of DM","Immunization","MCH","RNTCP","Study designs"],
        "ENT": ["Otitis media","Tonsillitis","Epistaxis","Vertigo","Hearing loss"],
        "Ophthalmology": ["Cataract","Glaucoma","Diabetic retinopathy","Conjunctivitis","Refractive errors"],
    },
    "Final Year": {
        "Medicine": ["Diabetes mellitus","Hypertension","Heart attack (MI)","Pneumonia","Stroke"],
        "Surgery": ["Appendicitis","Cholelithiasis","Hernia","Breast carcinoma","Acute abdomen"],
        "OBG": ["Pre-eclampsia","Postpartum hemorrhage","PCOS","Labour stages","Antepartum hemorrhage"],
        "Paediatrics": ["Childhood pneumonia","Acute diarrhea","Neonatal jaundice","Malnutrition","Febrile seizures"],
        "Orthopaedics": ["Fractures","Osteoarthritis","Spinal injuries","Compartment syndrome","Bone tumors"],
    },
    "Internship": {
        "Dermatology": ["Psoriasis","Eczema","Leprosy","Acne","Vitiligo"],
        "Psychiatry": ["Schizophrenia","Depression","Bipolar disorder","Anxiety disorders","Substance use"],
        "Anaesthesia": ["General anaesthesia","Spinal anaesthesia","Pre-anaesthetic checkup","Local anaesthetics","Airway management"],
        "Radiology": ["Chest X-ray basics","CT vs MRI","USG basics","Mammography","Contrast agents"],
    },
}

CT_ITEMS = [
    "I cross-check AI-generated notes with a standard textbook before trusting them.",
    "When AI gives an answer that contradicts my teacher, I assume the teacher is correct.",
    "I can usually identify factual errors in AI-generated medical content.",
    "I prefer AI notes over textbooks because they save time.",                # reverse-scored
    "I evaluate the reasoning behind an answer, not just the final answer.",
]
CT_REVERSE = [3]  # index of reverse-scored item

RSPQ = [
    "I find that studying sometimes gives me a feeling of deep personal satisfaction.",       #0 deep
    "I have to work a topic until I form my own conclusions before I am satisfied.",          #1 deep
    "My aim is to pass the course while doing as little work as possible.",                   #2 surface
    "I only study seriously what is given out in class or in the course outline.",            #3 surface
    "I feel that virtually any topic can be highly interesting once I get into it.",          #4 deep
    "I find most new topics interesting and spend extra time getting more information.",      #5 deep
    "I do not find my course interesting so I keep my work to the minimum.",                  #6 surface
    "I learn things by rote, going over them until I know them by heart even if I don't understand.", #7 surface
    "I find that studying academic topics can at times be as exciting as a good novel or movie.",     #8 deep
    "I test myself on important topics until I understand them completely.",                  #9 deep
    "I can get by in most assessments by memorizing key sections rather than understanding.", #10 surface
    "I generally restrict my study to what is specifically set, as extra work is unnecessary.",#11 surface
    "I work hard at my studies because I find the material interesting.",                     #12 deep
    "I spend free time finding out more about interesting topics discussed in classes.",      #13 deep
    "I find the best way to pass exams is to remember answers to likely questions.",          #14 surface
    "I find it is not helpful to study topics in depth; it just confuses and wastes time.",   #15 surface
    "I come to most classes with questions I want answered.",                                 #16 deep
    "I make a point of looking at most of the suggested readings for lectures.",              #17 deep
    "I see little point in learning material that is not likely to be in the exam.",          #18 surface
    "I find it best to memorize the textbook definition even if I don't fully grasp it.",     #19 surface
]
DEEP_IDX = [0,1,4,5,8,9,12,13,16,17]
SURFACE_IDX = [2,3,6,7,10,11,14,15,18,19]

LIKERT = ["1 - Strongly disagree","2 - Disagree","3 - Neutral","4 - Agree","5 - Strongly agree"]

def appscript(payload):
    try:
        r = requests.post(APPSCRIPT_URL, data=json.dumps(payload), timeout=20)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def build_prompt(year, subject, topic):
    return f"""You are generating assessment items for an MBBS undergraduate medical-education research questionnaire in India.
Year of study: {year}
Subject: {subject}
Topic: {topic}

Use standard Indian MBBS textbooks for accuracy (BD Chaurasia, Guyton, Ganong, Harper, Vasudevan, Robbins, Harsh Mohan, KD Tripathi, Katzung, Ananthanarayan, Park, Harrison's, Davidson's, Bailey & Love, SRB, Dutta, Williams, Ghai, Nelson, Dhingra, Khurana, Maheshwari, Neena Khanna, Niraj Ahuja, Ajay Yadav).

Output STRICT JSON ONLY. No markdown, no code fences, no commentary. Exactly this structure:
{{
 "factual":[
  {{"question":"<recall question>","options":["A) ...","B) ...","C) ...","D) ..."],"correct":"A"}},
  {{"question":"<recall question>","options":["A) ...","B) ...","C) ...","D) ..."],"correct":"B"}}
 ],
 "clinical":{{"question":"<short patient scenario>","options":["A) ...","B) ...","C) ...","D) ..."],"correct":"C"}},
 "critical":{{"question":"An AI chatbot tells you this about {topic}: '<a plausible but clearly INCORRECT statement - wrong dose / wrong contraindication / outdated guideline>'. What is the most appropriate action?","options":["A) Accept it and memorize for the exam","B) Note it down and move on without checking","C) Cross-check it with a standard textbook","D) Ask my clinical teacher or consultant"],"correct":"C"}}
}}
Rules:
- 2 factual items = Bloom level 1 recall (definitions, normal values, classifications) for {topic}.
- clinical item = Bloom level 3 application, single best diagnosis or first-line management.
- Difficulty matched to a year-{year} Indian MBBS student.
- 'correct' is exactly one of "A","B","C","D".
- The critical item's embedded AI error must be specific and factually wrong about {topic}.
- Return ONLY the JSON object."""

def get_questions(year, subject, topic):
    key = f"{year}|{subject}|{topic}"
    cached = appscript({"action":"get_cache","key":key})
    if cached.get("found"):
        try:
            return json.loads(cached["data"])
        except Exception:
            pass
    for _ in range(2):
        try:
            resp = MODEL.generate_content(build_prompt(year, subject, topic))
            text = resp.text.strip().replace("```json","").replace("```","").strip()
            data = json.loads(text)
            appscript({"action":"save_cache","key":key,"data":json.dumps(data)})
            return data
        except Exception:
            continue
    return None

def letter(choice):
    return choice.strip()[0].upper() if choice else ""

ss = st.session_state
if "step" not in ss:
    ss.step = "consent"
    ss.sid = str(uuid.uuid4())[:8]
    ss.demo = {}
    ss.rows = []
    ss.q = None

st.title("AI Notes & Learning — MBBS Research Survey")

# ---------- CONSENT ----------
if ss.step == "consent":
    st.write("This survey studies how AI-generated study notes relate to clinical reasoning, "
             "memory and critical thinking among MBBS students. It takes about 10–15 minutes. "
             "Responses are anonymous and used only for research.")
    if st.checkbox("I consent to participate."):
        if st.button("Start"):
            ss.step = "demo"; st.rerun()

# ---------- DEMOGRAPHICS ----------
elif ss.step == "demo":
    st.subheader("About you")
    age = st.number_input("Age", 17, 40, 20)
    gender = st.radio("Gender", ["Male","Female","Prefer not to say"])
    college = st.text_input("College name")
    year = st.selectbox("Year of MBBS", list(TOPICS.keys()))
    hours = st.number_input("Hours of self-study per day", 0, 18, 3)
    freq = st.selectbox("How often do you use AI for studying?",
                        ["Never","Rarely","Sometimes","Often","Daily"])
    tools = st.multiselect("Which AI tools do you use?",
                           ["ChatGPT","Gemini","Claude","Perplexity","NotebookLM","Meta AI","Other"])
    if st.button("Continue"):
        ss.demo = {"age":age,"gender":gender,"college":college,"year":year,
                   "hours":hours,"freq":freq,"tools":", ".join(tools)}
        ss.step = "topic"; st.rerun()

# ---------- TOPIC LOOP ----------
elif ss.step == "topic":
    year = ss.demo["year"]
    st.subheader(f"Topic {len(ss.rows)+1}")
    subject = st.selectbox("Subject", list(TOPICS[year].keys()))
    options = TOPICS[year][subject] + ["Other (type below)"]
    pick = st.selectbox("Topic you studied using AI", options)
    topic = st.text_input("Type your topic") if pick == "Other (type below)" else pick
    recency = st.selectbox("When did you LAST use AI for this topic?",
        ["Today","Within the past week","Within the past month","1–3 months ago",
         "3–6 months ago","More than 6 months ago"])
    pct = st.slider("What % of your notes on this topic came from AI?", 0, 100, 50)
    cross = st.selectbox("Did you cross-check the AI notes with a textbook?",
        ["Always","Sometimes","Rarely","Never"])

    if st.button("Generate questions for this topic"):
        if not topic:
            st.warning("Please choose or type a topic.")
        else:
            with st.spinner("Generating questions…"):
                ss.q = get_questions(year, subject, topic)
            ss.meta = {"subject":subject,"topic":topic,"recency":recency,"pct":pct,"cross":cross}
            if ss.q is None:
                st.error("Could not generate questions. Click the button again.")

    if ss.q:
        q = ss.q
        st.markdown("**Answer these questions:**")
        f1 = st.radio(q["factual"][0]["question"], q["factual"][0]["options"], key="f1")
        f2 = st.radio(q["factual"][1]["question"], q["factual"][1]["options"], key="f2")
        cl = st.radio(q["clinical"]["question"], q["clinical"]["options"], key="cl")
        cr = st.radio(q["critical"]["question"], q["critical"]["options"], key="cr")
        conf = st.slider("Without revising, how confident are you on this topic for a viva today? "
                         "(1 = not at all, 5 = very confident)", 1, 5, 3, key="conf")

        if st.button("Save this topic"):
            m = ss.meta
            f1c = 1 if letter(f1)==q["factual"][0]["correct"].upper() else 0
            f2c = 1 if letter(f2)==q["factual"][1]["correct"].upper() else 0
            clc = 1 if letter(cl)==q["clinical"]["correct"].upper() else 0
            crc = 1 if letter(cr) in ["C","D"] else 0
            fpct = round((f1c+f2c)/2*100)
            ss.rows.append({
                "subject":m["subject"],"topic":m["topic"],"recency":m["recency"],
                "pct":m["pct"],"cross":m["cross"],"f1":f1c,"f2":f2c,"cl":clc,
                "cr":crc,"fpct":fpct,"conf":conf})
            ss.q = None
            ss.step = "more"; st.rerun()

# ---------- ANOTHER TOPIC? ----------
elif ss.step == "more":
    st.success(f"Saved. You have completed {len(ss.rows)} topic(s).")
    c1, c2 = st.columns(2)
    if c1.button("Add another topic"):
        ss.step = "topic"; st.rerun()
    if c2.button("Finish — go to final questions"):
        ss.step = "scales"; st.rerun()

# ---------- FINAL SCALES ----------
elif ss.step == "scales":
    st.subheader("Final section — your study habits")
    st.markdown("**Part 1: rate your agreement**")
    ct = [LIKERT.index(st.radio(item, LIKERT, key=f"ct{i}"))+1 for i,item in enumerate(CT_ITEMS)]
    st.markdown("**Part 2: how you usually study (R-SPQ-2F)**")
    rs = [LIKERT.index(st.radio(item, LIKERT, key=f"rs{i}"))+1 for i,item in enumerate(RSPQ)]

    if st.button("Submit my responses"):
        ct_scored = [(6-v) if i in CT_REVERSE else v for i,v in enumerate(ct)]
        ct_total = sum(ct_scored)
        deep = sum(rs[i] for i in DEEP_IDX)
        surface = sum(rs[i] for i in SURFACE_IDX)
        d = ss.demo
        with st.spinner("Saving…"):
            for r in ss.rows:
                row = [datetime.now().isoformat(), ss.sid, d["age"], d["gender"], d["college"],
                       d["year"], d["hours"], d["freq"], d["tools"], r["subject"], r["topic"],
                       r["recency"], r["pct"], r["cross"], r["f1"], r["f2"], r["cl"], r["cr"],
                       r["fpct"], r["conf"], ct[0],ct[1],ct[2],ct[3],ct[4], ct_total, deep, surface]
                appscript({"action":"save_response","row":row})
        ss.step = "done"; st.rerun()

# ---------- DONE ----------
elif ss.step == "done":
    st.balloons()
    st.success("Thank you! Your responses have been recorded.")
    st.write("You may close this tab.")
