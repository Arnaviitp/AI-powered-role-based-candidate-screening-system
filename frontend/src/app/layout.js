import "./globals.css";

export const metadata = {
  title: "ScreenAI - AI Candidate Screening",
  description:
    "AI-powered role-based candidate screening with resume-aware interview questions and structured scoring.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <nav className="navbar">
          <div className="container navbar-inner">
            <a href="/" className="navbar-brand" aria-label="ScreenAI home">
              <span className="logo-icon" aria-hidden="true">
                S
              </span>
              <span>ScreenAI</span>
            </a>
            <div className="navbar-actions">
              <a href="/dashboard" className="btn btn-ghost btn-sm">
                Sessions
              </a>
              <a href="/" className="btn btn-ghost btn-sm">
                + New Interview
              </a>
            </div>
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
