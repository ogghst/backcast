import { useState } from "react";
import { Header } from "./Header";
import "./header.css";

export function HeaderTest() {
  const [user, setUser] = useState<{ name: string } | undefined>(undefined);
  const [theme, setTheme] = useState<"light" | "dark">("light");

  const toggleTheme = () => setTheme((prev) => (prev === "light" ? "dark" : "light"));

  return (
    <div
      style={{
        minHeight: "100vh",
        background: theme === "light" ? "#faf8f5" : "#0a0a0a",
        color: theme === "light" ? "#0a0a0a" : "#faf8f5",
        fontFamily: "'DM Sans', sans-serif",
        transition: "background 0.3s ease, color 0.3s ease",
      }}
    >
      <Header
        user={user}
        onLogin={() => setUser({ name: "Demo User" })}
        onLogout={() => setUser(undefined)}
        onCreateAccount={() => setUser({ name: "New User" })}
      />

      <main style={{ padding: "2rem", maxWidth: "800px", margin: "0 auto" }}>
        <h1 style={{ fontFamily: "'Playfair Display', serif", fontSize: "2.5rem", marginBottom: "1rem" }}>
          Header Component Test
        </h1>

        <section style={{ marginBottom: "2rem" }}>
          <h2 style={{ fontSize: "1.25rem", marginBottom: "0.75rem" }}>User State</h2>
          <p style={{ marginBottom: "1rem", opacity: 0.8 }}>
            Current: {user ? `Logged in as ${user.name}` : "Not logged in"}
          </p>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <button
              onClick={() => setUser({ name: "Demo User" })}
              style={{
                padding: "0.5rem 1rem",
                background: user ? "rgba(10, 10, 10, 0.1)" : "#c44536",
                color: user ? "inherit" : "#fff",
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
                fontFamily: "inherit",
              }}
            >
              Login
            </button>
            <button
              onClick={() => setUser(undefined)}
              style={{
                padding: "0.5rem 1rem",
                background: !user ? "rgba(10, 10, 10, 0.1)" : "#c44536",
                color: !user ? "inherit" : "#fff",
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
                fontFamily: "inherit",
              }}
            >
              Logout
            </button>
          </div>
        </section>

        <section style={{ marginBottom: "2rem" }}>
          <h2 style={{ fontSize: "1.25rem", marginBottom: "0.75rem" }}>Theme</h2>
          <button
            onClick={toggleTheme}
            style={{
              padding: "0.5rem 1rem",
              background: theme === "light" ? "#0a0a0a" : "#faf8f5",
              color: theme === "light" ? "#faf8f5" : "#0a0a0a",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            Toggle to {theme === "light" ? "Dark" : "Light"}
          </button>
        </section>

        <section style={{ marginBottom: "2rem" }}>
          <h2 style={{ fontSize: "1.25rem", marginBottom: "0.75rem" }}>Responsive Breakpoints</h2>
          <p style={{ opacity: 0.8, lineHeight: 1.6 }}>
            <strong>Desktop (&gt;1024px):</strong> Full layout with welcome text<br />
            <strong>Tablet (768-1024px):</strong> Condensed spacing, welcome hides at 850px<br />
            <strong>Mobile (&lt;768px):</strong> Hamburger menu with slide-in drawer
          </p>
        </section>

        <section>
          <h2 style={{ fontSize: "1.25rem", marginBottom: "0.75rem" }}>Design Features</h2>
          <ul style={{ opacity: 0.8, lineHeight: 1.8 }}>
            <li>Playfair Display (serif) for logo, DM Sans (geometric) for body</li>
            <li>Smooth hamburger → X transform animation</li>
            <li>Staggered reveal animations for drawer items</li>
            <li>Body scroll lock when menu is open</li>
            <li>Escape key to close menu</li>
            <li>Backdrop blur with overlay</li>
          </ul>
        </section>

        {/* Content to demonstrate scrolling behavior */}
        {Array.from({ length: 20 }).map((_, i) => (
          <p key={i} style={{ opacity: 0.6, marginTop: "1rem" }}>
            Section {i + 1}: Lorem ipsum dolor sit amet, consectetur adipiscing elit.
            Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
          </p>
        ))}
      </main>
    </div>
  );
}
