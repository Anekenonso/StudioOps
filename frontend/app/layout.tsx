import './globals.css'

export const metadata = {
  title: 'StudioOps - Demo',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="site-header">
          <div className="container">
            <h1 className="logo">StudioOps</h1>
            <p className="tag">Production intelligence</p>
          </div>
        </header>
        <main className="container">{children}</main>
      </body>
    </html>
  )
}
