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

export function taskIcon(name) {
  return iconMap[name] || Leaf
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