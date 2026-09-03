export const metadata = {
  title: 'StudioOps',
  description: 'Production intelligence workflow',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
