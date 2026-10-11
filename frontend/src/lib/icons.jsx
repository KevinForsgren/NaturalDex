import {
  Flower2, Sprout, Leaf, Bug, Sun, Compass, Layers, Star, TreePine, PenTool,
  MapPin, Sparkles, Clock, RefreshCw, Thermometer, GitMerge, CheckCircle, Trees,
  PawPrint, Bird, Rabbit, Users, Mountain, Flame, Target, Scan,
  BookmarkPlus, ZoomIn, BookOpen,
} from "lucide-react"

// Map backend/demo icon-slug names to lucide icons. Unknown names fall back to Leaf.
const iconMap = {
  Flower2, Sprout, Leaf, Bug, Sun, Compass, Layers, Star, TreePine, PenTool,
  MapPin, Sparkles, Clock, RefreshCw, Thermometer, GitMerge, CheckCircle, Trees,
  PawPrint, Bird, Rabbit, Users, Mountain, Flame, Target, Scan,
  BookmarkPlus, ZoomIn, BookOpen,
}

// The backend seeds catalog icons as kebab-case slugs; map them to lucide too.
const slugMap = {
  leaf: Leaf, flower: Flower2, "flower-2": Flower2, scan: Scan, sprout: Sprout,
  "tree-deciduous": TreePine, "tree-pine": TreePine, trees: Trees,
  "refresh-cw": RefreshCw, "paw-print": PawPrint, bird: Bird, bug: Bug,
  rabbit: Rabbit, users: Users, mushroom: Sprout, "map-pin": MapPin, target: Target,
  "bookmark-plus": BookmarkPlus, sun: Sun, "zoom-in": ZoomIn, mountain: Mountain,
  flame: Flame, sparkles: Sparkles, "check-circle": CheckCircle, "pen-tool": PenTool,
  compass: Compass, star: Star, clock: Clock, thermometer: Thermometer,
  "git-merge": GitMerge, layers: Layers,
}

export function taskIcon(name) {
  if (!name) return Leaf
  const key = String(name)
  if (iconMap[key]) return iconMap[key]
  if (slugMap[key]) return slugMap[key]
  return Leaf
}

export function categoryIcon(cat) {
  if (cat === "flora") return Flower2
  if (cat === "fungi") return Sprout
  if (cat === "fauna") return Bug
  return Leaf
}

export function CategoryBadge({ category }) {
  const C = categoryIcon(category)
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-nat-sage/70 text-nat-forest rounded-full text-[10px] font-semibold capitalize">
      <C className="w-3 h-3" /> {category}
    </span>
  )
}