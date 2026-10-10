import React from "react"
import { Compass, Grid3x3, BookOpen, User } from "lucide-react"
import { NavLink } from "react-router-dom"

const links = [
  { to: "/", label: "Explore", icon: Compass, end: true },
  { to: "/collection", label: "Collection", icon: Grid3x3 },
  { to: "/journal", label: "Journal", icon: BookOpen },
  { to: "/profile", label: "Profile", icon: User },
]

export default function BottomNav() {
  return (
    <nav className="fixed bottom-0 inset-x-0 mx-auto max-w-md z-40 bg-nat-bg/95 backdrop-blur-md border-t border-nat-border px-3 py-2 flex items-center justify-around shadow-lg">
      {links.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            `flex flex-col items-center gap-1 transition-colors ${
              isActive ? "text-nat-forest font-semibold" : "text-nat-muted hover:text-nat-forest"
            }`
          }
        >
          <Icon className="w-5 h-5" />
          <span className="text-[10px] tracking-tight">{label}</span>
        </NavLink>
      ))}
    </nav>
  )
}