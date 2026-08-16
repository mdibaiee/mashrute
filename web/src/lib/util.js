// Deterministic hash from an id, so a person's colour never changes.
function hashOf(id) {
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) % 100003;
  return h;
}

// Avatars and group marks draw from the four tilework colours rather than the
// whole spectrum, so a page full of them still reads as one palette. Each entry
// is a [from, to] pair for the disc's gradient.
export const PALETTE = [
  ['#3fc9db', '#1b8fa6'],  // fīrūza — turquoise
  ['#263991', '#152163'],  // lāzhvard — lapis
  ['#d2588b', '#a33463'],  // rose
  ['#1cb680', '#0d7d57'],  // garden green
  ['#4a63c8', '#263991'],  // lapis, lighter cast
  ['#26a8bd', '#166b7e'],  // deep turquoise
];
export function paletteOf(id) {
  return PALETTE[hashOf(id) % PALETTE.length];
}

// Kept for callers that want a raw hue (group header marks).
export function hueOf(id) {
  return hashOf(id) % 360;
}

// Initials for the avatar. Latin names give up to two letters; we strip the
// honorific particles that would otherwise make half the cast read "AL".
const SKIP = new Set(['al', 'al-', 'the', 'of', 'ibn', 'bin', 'abu', 'mirza', 'sir', 'dr.', 'dr']);
export function initials(nameEn) {
  const parts = nameEn
    .replace(/[''‘’"()]/g, ' ')
    .split(/[\s-]+/)
    .filter((w) => w && !SKIP.has(w.toLowerCase()));
  if (!parts.length) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export const GROUP_TYPE_LABEL = {
  anjuman: ['Anjuman / council', 'انجمن'],
  political_party: ['Political party', 'حزب سیاسی'],
  secret_society: ['Secret society', 'انجمن سری'],
  militia: ['Militia', 'نیروی مسلح'],
  religious_community: ['Religious community', 'جامعهٔ دینی'],
  religious_faction: ['Religious faction', 'جناح دینی'],
  ethnic_group: ['Ethnic group', 'گروه قومی'],
  tribe: ['Tribe', 'ایل'],
  guild: ['Guild', 'صنف'],
  state_institution: ['State institution', 'نهاد دولتی'],
  foreign_power: ['Foreign power', 'قدرت خارجی'],
  international_org: ['International body', 'نهاد بین‌المللی'],
  newspaper: ['Newspaper', 'روزنامه'],
  school: ['School', 'مدرسه'],
  social_class: ['Social class', 'طبقهٔ اجتماعی'],
  womens_organization: ["Women's organisation", 'انجمن زنان'],
};

export const EVENT_TYPE_LABEL = {
  protest: ['Protest', 'اعتراض'], strike: ['Strike', 'اعتصاب'],
  sanctuary: ['Sanctuary (bast)', 'بست'], assassination: ['Assassination', 'ترور'],
  execution: ['Execution', 'اعدام'], battle: ['Battle', 'نبرد'], siege: ['Siege', 'محاصره'],
  coup: ["Coup d'état", 'کودتا'], election: ['Election', 'انتخابات'],
  legislation: ['Legislation', 'قانون‌گذاری'], decree: ['Decree', 'فرمان'],
  treaty: ['Treaty', 'عهدنامه'], publication: ['Publication', 'انتشار'],
  founding: ['Founding', 'تأسیس'], dissolution: ['Dissolution', 'انحلال'],
  appointment: ['Appointment', 'انتصاب'], dismissal: ['Dismissal', 'برکناری'],
  exile: ['Exile', 'تبعید'], massacre: ['Massacre', 'کشتار'],
  occupation: ['Occupation', 'اشغال'], ultimatum: ['Ultimatum', 'اولتیماتوم'],
  conference: ['Conference', 'کنفرانس'], death: ['Death', 'درگذشت'],
  uprising: ['Uprising', 'قیام'], reform: ['Reform', 'اصلاحات'], other: ['Other', 'دیگر'],
};

// Persian-Indic digits, so a year pill in Persian mode reads ۱۲۸۵ rather than
// sitting in Latin numerals among Persian text.
const FA_DIGITS = '۰۱۲۳۴۵۶۷۸۹';
export function faDigits(s) {
  return String(s).replace(/[0-9]/g, (d) => FA_DIGITS[+d]);
}

// Persian has no initialism convention the way English does, so a two-letter
// monogram from the distinguishing part of the name reads better than one
// letter per word. Honorifics carry no identity, so they are skipped.
const FA_SKIP = new Set(['سید', 'سيد', 'میرزا', 'شیخ', 'حاج', 'حاجی', 'آقا', 'ملا',
                         'حجت‌الاسلام', 'آیت‌الله', 'خان', 'میر', 'سردار', 'سالار',
                         'دکتر', 'مستر', 'ژنرال', 'کلنل', 'سر']);
export function initialsFa(nameFa) {
  if (!nameFa) return '';
  // ZWNJ joins the halves of one compound word (تقی‌زاده), so it must not be
  // treated as a word break — splitting there would monogram "زا", not "تق".
  const parts = nameFa
    .replace(/[«»"'()]/g, ' ')
    .split(/[\s‏‎-]+/)
    .filter((w) => w && !FA_SKIP.has(w));
  const word = parts[parts.length - 1] || nameFa.trim();
  const two = word.slice(0, 2);
  return two.charCodeAt(1) === 0x200c ? word.slice(0, 3) : two;
}
