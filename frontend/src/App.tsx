import { useEffect, useRef, useState, type FormEvent } from 'react';
import { ArrowLeft, ArrowUp, ArrowUpRight, BookOpen, Check, Github, Languages, Linkedin, LoaderCircle, Plus, Settings2, SlidersHorizontal, X } from 'lucide-react';
import { copy, type Language } from './content';

type ResultLanguage = Language | 'both';
type Preferences = { language: Language; results: ResultLanguage; definitions: boolean };
type Suggestion = { word: string; definition: string; language: Language; part_of_speech?: string; score?: number };
type Turn = { query: string; words: Suggestion[]; sample: boolean };
const repo = 'https://github.com/Rohan-Ktksu/shabdanveshi';
const linkedin = 'https://www.linkedin.com/in/rohansai0907';
const key = 'shabdanveshi.preferences.v1';

function savedPreferences(): Preferences | null {
  try {
    const value = JSON.parse(localStorage.getItem(key) || 'null');
    if (value && ['en', 'hi'].includes(value.language) && ['en', 'hi', 'both'].includes(value.results) && typeof value.definitions === 'boolean') return value;
  } catch { /* Storage may be unavailable in private mode. */ }
  return null;
}

function Logo({ small = false }: { small?: boolean }) {
  return <span className={`logo ${small ? 'small' : ''}`}><span className="logo-mark" aria-hidden="true">श<span className="logo-dot" /></span>{!small && <span>Shabd<span className="brand-light">Anveshi</span></span>}</span>;
}

function LanguageDialog({ onSelect, onClose }: { onSelect: (language: Language) => void; onClose?: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { dialog.current?.showModal(); return () => { dialog.current?.close(); }; }, []);
  return <dialog ref={dialog} className="language-dialog" onCancel={event => { if (!onClose) event.preventDefault(); else onClose(); }} aria-labelledby="language-title">
    {onClose && <button className="icon-button close-dialog" onClick={onClose} aria-label="Close / बंद करें"><X size={20} /></button>}
    <Logo small /><p className="eyebrow">WELCOME · स्वागत है</p>
    <h1 id="language-title">Words begin with you.</h1><p className="hindi-welcome" lang="hi">आपकी भाषा, आपके शब्द।</p>
    <p className="dialog-intro">Choose your language to get started.<br /><span lang="hi">शुरू करने के लिए भाषा चुनें।</span></p>
    <div className="language-options"><button onClick={() => onSelect('en')}><span className="language-letter">Aa</span><strong>English</strong><span>Continue <ArrowUpRight size={15} /></span></button><button onClick={() => onSelect('hi')} lang="hi"><span className="language-letter">अ</span><strong>हिंदी</strong><span>आगे बढ़ें <ArrowUpRight size={15} /></span></button></div>
    <p className="small-note">You can change this anytime. / इसे कभी भी बदल सकते हैं।</p>
  </dialog>;
}

function route(): 'chat' | 'about' | 'settings' {
  return location.hash === '#about' ? 'about' : location.hash === '#settings' ? 'settings' : 'chat';
}

export default function App() {
  const initial = useRef(savedPreferences());
  const [preferences, setPreferences] = useState<Preferences>(initial.current || { language: 'en', results: 'en', definitions: true });
  const [languageOpen, setLanguageOpen] = useState(!initial.current);
  const [firstVisit, setFirstVisit] = useState(!initial.current);
  const [page, setPage] = useState(route);
  const [description, setDescription] = useState('');
  const [cluesOpen, setCluesOpen] = useState(false);
  const [letter, setLetter] = useState('');
  const [length, setLength] = useState('');
  const [pos, setPos] = useState('');
  const [turns, setTurns] = useState<Turn[]>([]);
  const [error, setError] = useState<keyof Pick<typeof copy.en, 'notConnected' | 'failed' | 'invalid'> | null>(null);
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLTextAreaElement>(null);
  const request = useRef<AbortController | null>(null);
  const t = copy[preferences.language];
  const en = preferences.language === 'en';
  useEffect(() => { const changed = () => setPage(route()); window.addEventListener('hashchange', changed); return () => window.removeEventListener('hashchange', changed); }, []);
  useEffect(() => { document.documentElement.lang = preferences.language; if (!firstVisit) try { localStorage.setItem(key, JSON.stringify(preferences)); } catch { /* Preferences still work for this visit. */ } }, [preferences, firstVisit]);
  useEffect(() => () => request.current?.abort(), []);

  function selectLanguage(language: Language) {
    setPreferences(current => ({ ...current, language, ...(firstVisit ? { results: language } : {}) }));
    setFirstVisit(false); setLanguageOpen(false);
  }
  function newSearch() {
    request.current?.abort(); request.current = null; setBusy(false); setTurns([]); setError(null); setDescription(''); setLetter(''); setLength(''); setPos(''); location.hash = ''; input.current?.focus();
  }
  function sample() {
    const hindi = preferences.results === 'hi';
    const englishWords: Suggestion[] = [{ word: 'Bibliophile', definition: 'A person who loves or collects books.', language: 'en', part_of_speech: 'noun' }, { word: 'Bookworm', definition: 'An informal word for someone who spends a lot of time reading.', language: 'en', part_of_speech: 'noun' }];
    const hindiWords: Suggestion[] = [{ word: 'पुस्तकप्रेमी', definition: 'वह व्यक्ति जिसे पुस्तकें पढ़ने या संग्रह करने का शौक हो।', language: 'hi', part_of_speech: 'noun' }, { word: 'पाठक', definition: 'पढ़ने वाला व्यक्ति। यह व्यापक शब्द है; इसमें पुस्तकों के प्रति विशेष प्रेम का भाव आवश्यक नहीं है।', language: 'hi', part_of_speech: 'noun' }];
    setTurns([{ query: t.examples[0], words: preferences.results === 'both' ? [...englishWords, ...hindiWords] : hindi ? hindiWords : englishWords, sample: true }]); setError(null);
  }
  async function search(event?: FormEvent) {
    event?.preventDefault(); if (busy) return;
    if (input.current?.form && !input.current.form.reportValidity()) return;
    const query = description.trim();
    if (query.length < 3) { setError('invalid'); input.current?.focus(); return; }
    const api = import.meta.env.VITE_API_URL?.trim().replace(/\/$/, '');
    if (!api) { setError('notConnected'); return; }
    setBusy(true); setError(null);
    const controller = new AbortController(); request.current = controller;
    const timer = setTimeout(() => controller.abort(), 60000);
    try {
      const response = await fetch(`${api}/api/predict`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: controller.signal, body: JSON.stringify({ description: query, language: preferences.results, starting_letter: letter.trim() || null, approximate_length: length ? Number(length) : null, part_of_speech: pos || null, limit: 5 }) });
      if (!response.ok) throw new Error('Prediction failed');
      const data: unknown = await response.json();
      if (!data || typeof data !== 'object' || !('suggestions' in data) || !Array.isArray(data.suggestions)) throw new Error('Invalid response');
      const valid = data.suggestions.every((item: unknown): item is Suggestion => !!item && typeof item === 'object' && 'word' in item && typeof item.word === 'string' && 'definition' in item && typeof item.definition === 'string' && 'language' in item && ['en', 'hi'].includes(String(item.language)) && (!('score' in item) || typeof item.score === 'number' && Number.isFinite(item.score)));
      if (!valid) throw new Error('Invalid suggestions');
      if (request.current !== controller) return;
      const suggestions = data.suggestions.slice(0, 5) as Suggestion[];
      setTurns(current => [...current, { query, words: suggestions, sample: false }]); setDescription('');
    } catch { if (request.current === controller) setError('failed'); }
    finally { clearTimeout(timer); if (request.current === controller) { setBusy(false); request.current = null; } }
  }

  return <div className="app-shell"><a className="skip-link" href="#main">{en ? 'Skip to content' : 'मुख्य भाग पर जाएँ'}</a>
    <header className="site-header"><a href="#" className="brand-link" aria-label="ShabdAnveshi home"><Logo /></a><nav aria-label={en ? 'Main navigation' : 'मुख्य नेविगेशन'}><a className={page === 'about' ? 'nav-link active' : 'nav-link'} href="#about">{t.about}</a><span className="nav-divider" /><button className="language-button" onClick={() => setLanguageOpen(true)} aria-label={t.language}><Languages size={19} /><span>{en ? 'EN' : 'हिं'}</span></button><a href="#settings" className={`icon-button ${page === 'settings' ? 'active' : ''}`} aria-label={t.settings}><Settings2 size={20} /></a></nav></header>
    <main id="main">
      {page === 'chat' && <section className="chat-page"><div className="chat-heading"><p className="eyebrow"><span className="tiny-line" />{t.eyebrow}</p><h1>{t.title}<br /><em>{t.titleEnd}</em></h1><p className="intro-copy">{t.intro}</p></div>
        {turns.length === 0 && <div className="examples">{t.examples.map(example => <button key={example} onClick={() => { setDescription(example); setError(null); input.current?.focus(); }}>{example}<ArrowUpRight size={14} /></button>)}</div>}
        {turns.length > 0 && <div className="conversation" aria-live="polite">{turns.map((turn, i) => <article className="turn" key={i}><p className="user-message">{turn.query}</p><div className="assistant-message"><Logo small /><div className="answer-body">{turn.sample && <p className="sample-label"><BookOpen size={13} />{t.demo}</p>}<p className="answer-intro">{turn.words.length ? t.suggestions : t.noResults}</p>{turn.words.map((word, index) => <div className="word-result" key={`${word.language}-${word.word}-${index}`}><div className="word-heading"><h2 lang={word.language}>{word.word}</h2><span>{word.part_of_speech && word.part_of_speech in t ? String(t[word.part_of_speech as keyof typeof t]) : word.part_of_speech}</span><span className="word-language">{word.language === 'hi' ? 'हिंदी' : 'EN'}</span></div>{preferences.definitions && <p lang={word.language}>{word.definition}</p>}{word.score !== undefined && <span className="score">{t.match}: {word.score.toFixed(3)}</span>}</div>)}</div></div></article>)}<button className="text-button" onClick={newSearch}><Plus size={16} />{t.newChat}</button></div>}
        <form className="composer" onSubmit={search}><label className="sr-only" htmlFor="description">{t.placeholder}</label><textarea id="description" ref={input} value={description} maxLength={1000} rows={3} placeholder={t.placeholder} onChange={e => setDescription(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void search(); } }} />
          {cluesOpen && <div className="clue-fields"><label>{t.first}<input value={letter} maxLength={8} onChange={e => setLetter(e.target.value)} placeholder={en ? 'e.g. b' : 'जैसे प'} /></label><label>{t.length}<input type="number" min={1} max={60} value={length} onChange={e => setLength(e.target.value)} /></label><label>{t.pos}<select value={pos} onChange={e => setPos(e.target.value)}><option value="">{t.any}</option>{(['noun', 'verb', 'adjective', 'adverb'] as const).map(value => <option value={value} key={value}>{t[value]}</option>)}</select></label></div>}
          <div className="composer-tools"><button type="button" className={`clue-toggle ${cluesOpen ? 'active' : ''}`} aria-expanded={cluesOpen} onClick={() => setCluesOpen(!cluesOpen)}><SlidersHorizontal size={16} />{t.clues}</button><div className="composer-right"><select aria-label={t.results} value={preferences.results} onChange={e => setPreferences({ ...preferences, results: e.target.value as ResultLanguage })}><option value="en">English</option><option value="hi">हिंदी</option><option value="both">{t.both}</option></select><button className="send-button" disabled={busy} type="submit"><span>{busy ? t.searching : t.search}</span>{busy ? <LoaderCircle className="spinning" size={17} /> : <ArrowUp size={17} />}</button></div></div>
        </form><p className="input-hint">{t.hint}</p>{error && <p className="error-message" role="alert">{t[error]}</p>}{turns.length === 0 && <button className="sample-button" onClick={sample}><BookOpen size={16} />{t.sample}<ArrowUpRight size={14} /></button>}
      </section>}
      {page === 'settings' && <section className="settings-page"><a className="back-link" href="#"><ArrowLeft size={16} />{t.back}</a><p className="eyebrow">SHABDANVESHI</p><h1>{t.settings}</h1><p className="intro-copy">{t.settingsIntro}</p><div className="setting-row"><label htmlFor="ui-language">{t.ui}</label><select id="ui-language" value={preferences.language} onChange={e => selectLanguage(e.target.value as Language)}><option value="en">English</option><option value="hi">हिंदी</option></select></div><div className="setting-row"><label htmlFor="result-language">{t.results}</label><select id="result-language" value={preferences.results} onChange={e => setPreferences({ ...preferences, results: e.target.value as ResultLanguage })}><option value="en">English</option><option value="hi">हिंदी</option><option value="both">{t.both}</option></select></div><div className="setting-row"><label htmlFor="definitions">{t.definitions}</label><input id="definitions" type="checkbox" checked={preferences.definitions} onChange={e => setPreferences({ ...preferences, definitions: e.target.checked })} /></div><p className="preference-note"><Check size={15} />{t.saved}</p></section>}
      {page === 'about' && <About language={preferences.language} />}
    </main><footer className="site-footer"><span>शब्दान्वेषी <span className="footer-dot">·</span> {t.footer}</span><a href={repo} target="_blank" rel="noopener noreferrer"><Github size={16} /><span>GitHub</span><ArrowUpRight size={12} /></a></footer>
    {languageOpen && <LanguageDialog onSelect={selectLanguage} onClose={firstVisit ? undefined : () => setLanguageOpen(false)} />}
  </div>;
}

function About({ language }: { language: Language }) {
  const t = copy[language]; const en = language === 'en';
  const tools = [
    ['React · TypeScript · Vite', en ? 'In use' : 'इस्तेमाल में', en ? 'The responsive chat, bilingual interface and typed API integration.' : 'रेस्पॉन्सिव चैट, द्विभाषी इंटरफ़ेस और API का संयोजन।'],
    ['Python · FastAPI', en ? 'Planned' : 'प्रस्तावित', en ? 'The service that receives descriptions and returns ranked words.' : 'विवरण लेकर क्रमबद्ध शब्द सुझाव लौटाने वाली सेवा।'],
    ['Sentence Transformers', en ? 'Planned' : 'प्रस्तावित', en ? 'Multilingual embeddings for matching meanings. Model selection will follow testing.' : 'अर्थ मिलान के लिए बहुभाषी embeddings। परीक्षण के बाद मॉडल चुना जाएगा।'],
    ['scikit-learn', en ? 'Planned' : 'प्रस्तावित', en ? 'TF-IDF and cosine similarity provide a keyword baseline.' : 'TF-IDF और cosine similarity कीवर्ड मिलान का आधार हैं।'],
    ['NLTK · WordNet', en ? 'Planned' : 'प्रस्तावित', en ? 'English definitions and word senses. Hindi needs a separately licensed lexical resource; English WordNet alone is insufficient.' : 'अंग्रेज़ी के अर्थ और परिभाषाएँ। हिंदी के लिए अलग, उपयुक्त लाइसेंस वाला शब्द-संसाधन चाहिए।'],
  ];
  const details = ['R24EJ042', 'CSIT A', en ? '5th Semester' : '5वाँ सेमेस्टर', 'Natural Language Processing', 'B25EJS503', 'Arati C', 'Similar Word Prediction'];
  return <article className="about-page"><a className="back-link" href="#"><ArrowLeft size={16} />{t.back}</a><div className="about-hero"><p className="eyebrow">{t.storyLabel}</p><h1>{t.storyTitle}<br /><em>{t.storyEnd}</em></h1><p className="intro-copy">{t.story}</p><span className="stage-note"><span />{t.stage}</span></div><section className="about-section"><div className="section-label">01 / {en ? 'THE JOURNEY' : 'यात्रा'}</div><h2>{t.journey}</h2><ol className="timeline">{t.steps.map(([title, body]) => <li key={title}><h3>{title}</h3><p>{body}</p></li>)}</ol></section><section className="about-section"><div className="section-label">02 / {en ? 'THE LOGIC' : 'तर्क'}</div><h2>{t.logicTitle}</h2><ol className="logic-list">{t.logic.map((item, i) => <li key={item}><span>{String(i + 1).padStart(2, '0')}</span><p>{item}</p></li>)}</ol><p className="honest-note">{t.noGuarantee}</p></section><section className="about-section"><div className="section-label">03 / {en ? 'THE TOOLKIT' : 'तकनीक'}</div><h2>{t.toolkit}</h2><p>{t.toolkitNote}</p><dl className="tool-list">{tools.map(([name, status, description]) => <div key={name}><dt>{name}<span>{status}</span></dt><dd>{description}</dd></div>)}</dl></section><section className="about-section creator-section"><div className="section-label">04 / {en ? 'THE PERSON' : 'निर्माता'}</div><h2>{t.creator}</h2><div className="creator-heading"><div className="avatar">RS</div><div><h3>Gorumutchu Rohan Sai</h3><p>{t.creatorRole}</p></div></div><dl className="student-details">{details.map((detail, i) => <div key={t.labels[i]}><dt>{t.labels[i]}</dt><dd>{detail}</dd></div>)}</dl><div className="profile-links"><a href={linkedin} target="_blank" rel="noopener noreferrer"><Linkedin size={17} />LinkedIn<ArrowUpRight size={15} /></a><a href={repo} target="_blank" rel="noopener noreferrer"><Github size={17} />{t.repository}<ArrowUpRight size={15} /></a></div></section></article>;
}
