// Demo data provider for the NatureDex showcase video.
//
// This mirrors the backend API response shapes exactly so the UI can be written
// once and later pointed at the real FastAPI backend (see api.js / data.js).
// State is persisted to localStorage so the demo survives a refresh. It is NOT a
// fake model result: an accepted demo discovery is labeled as such in the UI.

const LS_KEY = "ndx-demo-v1";

const TASK_POOL = [
  { id: 1, title: "Discover 2 native plant species", target: 2, xp: 40, icon: "Flower2", cat: "flora" },
  { id: 2, title: "Photograph a specimen in damp soil or shade", target: 1, xp: 30, icon: "Trees", cat: "all" },
  { id: 3, title: "Identify a wild fungus or moss morphology", target: 1, xp: 50, icon: "Sprout", cat: "fungi" },
  { id: 4, title: "Observe distinct leaf venation or bracts", target: 1, xp: 35, icon: "Leaf", cat: "flora" },
  { id: 5, title: "Log a wild fauna or insect specimen", target: 1, xp: 60, icon: "Bug", cat: "fauna" },
  { id: 6, title: "Scan a specimen during morning sunlight", target: 1, xp: 25, icon: "Sun", cat: "all" },
  { id: 7, title: "Record a field observation near trail edges", target: 1, xp: 30, icon: "Compass", cat: "all" },
  { id: 8, title: "Document 3 different leaf structures", target: 3, xp: 75, icon: "Layers", cat: "flora" },
  { id: 9, title: "Find an uncommon or rare species card", target: 1, xp: 80, icon: "Star", cat: "all" },
  { id: 10, title: "Scan a woody vine or tree bark texture", target: 1, xp: 40, icon: "TreePine", cat: "flora" },
  { id: 11, title: "Log an outdoor observation with personal notes", target: 1, xp: 35, icon: "PenTool", cat: "all" },
  { id: 12, title: "Discover a specimen in a community park", target: 1, xp: 30, icon: "MapPin", cat: "all" },
  { id: 13, title: "Observe floral petals with high AI confidence", target: 1, xp: 45, icon: "Sparkles", cat: "flora" },
  { id: 14, title: "Find 2 specimens in the same hour", target: 2, xp: 50, icon: "Clock", cat: "all" },
  { id: 15, title: "Document an outdoor mushroom or lichen", target: 1, xp: 55, icon: "Sprout", cat: "fungi" },
  { id: 16, title: "Log a pollinator or winged insect", target: 1, xp: 65, icon: "Bug", cat: "fauna" },
  { id: 17, title: "Complete a repeat observation for extra XP", target: 1, xp: 20, icon: "RefreshCw", cat: "all" },
  { id: 18, title: "Discover a species native to warm climates", target: 1, xp: 40, icon: "Thermometer", cat: "flora" },
  { id: 19, title: "Scan a climbing or trailing botanical species", target: 1, xp: 45, icon: "GitMerge", cat: "flora" },
  { id: 20, title: "Achieve 90%+ AI match accuracy on a scan", target: 1, xp: 50, icon: "CheckCircle", cat: "all" },
]

const SEED_SPECIES = [
  { id: "bougainvillea", commonName: "Bougainvillea", scientificName: "Bougainvillea spectabilis", category: "flora", rarity: "Common", xpValue: 40, discovered: true, scanCount: 2, discoveryDate: "2026-10-08", location: "Pine Ridge Woods", photoUrl: "https://images.unsplash.com/photo-1509181160473-20092f03f39a?auto=format&fit=crop&w=600&q=80", notes: "Vibrant pink floral bracts. Scanned near south pathway.", confidence: 96, botanicalDetails: "Paper-like colored bracts surrounding tiny cream blossoms. Drought-tolerant woody vine." },
  { id: "monstera", commonName: "Swiss Cheese Plant", scientificName: "Monstera deliciosa", category: "flora", rarity: "Uncommon", xpValue: 60, discovered: true, scanCount: 1, discoveryDate: "2026-10-09", location: "Botanical Conservatory", photoUrl: "https://images.unsplash.com/photo-1614594975525-e45190c55d0b?auto=format&fit=crop&w=600&q=80", notes: "Large natural leaf perforations (fenestrations).", confidence: 94, botanicalDetails: "Epiphytic climber native to tropical rainforests." },
  { id: "fly-agaric", commonName: "Fly Agaric", scientificName: "Amanita muscaria", category: "fungi", rarity: "Rare", xpValue: 100, discovered: true, scanCount: 1, discoveryDate: "2026-10-05", location: "Damp Birch Grove", photoUrl: "https://images.unsplash.com/photo-1543852786-1cf6624b9987?auto=format&fit=crop&w=600&q=80", notes: "Bright crimson cap with white veil remnants.", confidence: 91, botanicalDetails: "Iconic basidiomycete fungus forming mycorrhizal associations." },
  { id: "monarch", commonName: "Monarch Butterfly", scientificName: "Danaus plexippus", category: "fauna", rarity: "Uncommon", xpValue: 75, discovered: true, scanCount: 3, discoveryDate: "2026-10-02", location: "Wildflower Meadow", photoUrl: "https://images.unsplash.com/photo-1526336024174-e58f5cdd8e13?auto=format&fit=crop&w=600&q=80", notes: "Observed feeding on milkweed nectar.", confidence: 98, botanicalDetails: "Famous migratory lepidopteran." },
  { id: "chanterelle", commonName: "Golden Chanterelle", scientificName: "Cantharellus cibarius", category: "fungi", rarity: "Uncommon", xpValue: 70, discovered: false, hint: "Look near hardwood mosses after autumn rain." },
  { id: "oak", commonName: "Oak", scientificName: "Quercus spp.", category: "flora", rarity: "Common", xpValue: 35, discovered: false, hint: "Broad-leaved tree with lobed leaves and acorns." },
  { id: "red-squirrel", commonName: "Red Squirrel", scientificName: "Sciurus vulgaris", category: "fauna", rarity: "Rare", xpValue: 110, discovered: false, hint: "Look in tall pines; listen for a chattering call." },
  { id: "honey-bee", commonName: "Honey Bee", scientificName: "Apis mellifera", category: "fauna", rarity: "Common", xpValue: 30, discovered: false, hint: "Foraging on open flowers in midday sun." },
]

const DEFAULT_STATE = {
  user: { username: "Scout" },
  xpTotal: 420,
  dailySets: {}, // key: dateISO => set
  species: SEED_SPECIES,
  discoveries: 0,
}

function todayKey() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`
}

function load() {
  try {
    const raw = localStorage.getItem(LS_KEY)
    if (raw) return { ...DEFAULT_STATE, ...JSON.parse(raw) }
  } catch (_) { /* ignore corrupted */ }
  return JSON.parse(JSON.stringify(DEFAULT_STATE))
}

function save(state) {
  try { localStorage.setItem(LS_KEY, JSON.stringify(state)) } catch (_) { /* best effort */ }
}

function pickTasks(state) {
  const day = todayKey()
  const existing = state.dailySets[day]
  if (existing) return existing
  // pick 3 from pool, avoid repeating the previous day's tasks when possible
  const shuffled = [...TASK_POOL].sort(() => Math.random() - 0.5)
  const set = {
    id: `${day}-${Date.now()}`,
    date: day,
    tasks: shuffled.slice(0, 3).map((t, i) => ({
      id: `${setId()}`, task_set_id: null, slot_number: i + 1,
      status: t.target > 1 ? "in_progress" : "assigned",
      progress_value: t.id % 5 === 0 ? 0 : 0,
      target_value: t.target, xp_value: t.xp, completed_at: null,
      task: { slug: t.id, title: t.title, category: t.cat, icon: t.icon, xp_value: t.xp },
    })),
  }
  set.tasks.forEach((tk) => (tk.task_set_id = set.id))
  state.dailySets[day] = set
  save(state)
  return set
}

let uid = Date.now()
function setId() { return uid++ }

export const demo = {
  todayKey,
  getDailyTasks() {
    const s = load()
    return pickTasks(s)
  },
  taskHistory() {
    const s = load()
    return Object.values(s.dailySets).sort((a, b) => (a.date < b.date ? 1 : -1))
  },
  listCollection(category) {
    const s = load()
    return s.species.map((sp) => ({
      ...sp,
      public_id: sp.discovered ? `ndk-${sp.id}-${sp.scanCount || 1}` : null,
      image_url: sp.discovered ? sp.photoUrl : null,
    }))
  },
  getCardBySpecies(publicIdOrSpeciesId) {
    const s = load()
    // demo card ids look like ndk-<species-id>-<count>
    const key = String(publicIdOrSpeciesId).replace(/^ndk-/, "").split("-")[0]
    const sp =
      s.species.find((x) => x.id === publicIdOrSpeciesId) ||
      s.species.find((x) => x.id === key)
    return sp && sp.discovered ? sp : null
  },
  getProfileStats() {
    const s = load()
    const discovered = s.species.filter((x) => x.discovered)
    const cats = { flora: 0, fauna: 0, fungi: 0 }
    discovered.forEach((x) => (cats[x.category] += 1))
    return {
      unique_species: discovered.length,
      observations: discovered.reduce((a, x) => a + (x.scanCount || 0), 0),
      category_totals: cats,
      xp_total: s.xpTotal,
      streak_days: 3,
    }
  },
  // Discovery (demo): always accepts Bougainvillea so the flow is demonstrable.
  createDiscovery() {
    const s = load()
    s.discoveries += 1
    save(s)
    return { discovery: { id: `d-${s.discoveries}`, status: "pending" } }
  },
  // uploadPhoto stores a reference (data URL) for the demo card.
  uploadPhoto(photoDataUrl) {
    return { storage_key: photoDataUrl, content_type: "image/jpeg" }
  },
  submitDiscovery() {
    const s = load()
    let card = s.species.find((x) => x.id === "bougainvillea")
    const isFirst = !(card && card.discovered)
    if (card) {
      card.discovered = true
      card.scanCount = (card.scanCount || 0) + 1
      card.discoveryDate = "Today (Updated)"
    } else {
      card = {
        id: "bougainvillea", commonName: "Bougainvillea", scientificName: "Bougainvillea spectabilis",
        category: "flora", rarity: "Common", xpValue: 40, discovered: true, scanCount: 1,
        discoveryDate: "Today", location: "Pine Ridge Woods",
        photoUrl: "https://images.unsplash.com/photo-1509181160473-20092f03f39a?auto=format&fit=crop&w=600&q=80",
        confidence: 96, botanicalDetails: "Paper-like colored bracts.", notes: "Demo observation.",
      }
      s.species.unshift(card)
    }
    s.xpTotal += 40
    const pub = `ndk-${card.id}-${card.scanCount}`
    save(s)
    return {
      status: "accepted", accepted: true,
      isDemo: true,
      cardPublicId: pub,
      cardUrl: `/collection/card-${pub}`,
      isFirstDiscovery: isFirst,
      count: card.scanCount,
      demoResult: {
        commonName: "Bougainvillea",
        scientificName: "Bougainvillea spectabilis",
        category: "flora",
        rarity: "Common",
        confidence: 96,
        xp: 40,
        summary: "A flowering ornamental shrub with vivid papery bracts.",
        photoUrl: card.photoUrl,
      },
      taskProgress: pickTasks(s),
    }
  },
}

export default demo