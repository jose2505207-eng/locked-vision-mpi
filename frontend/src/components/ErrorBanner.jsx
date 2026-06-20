// Loud, unmissable status banner. Red on block, green on pass.
export default function ErrorBanner({ validation }) {
  if (!validation || !validation.message) return null;

  if (validation.status === "passed") {
    return <div className="ok-banner">✓ {validation.message}</div>;
  }
  return (
    <div className="error-banner">
      <span style={{ fontSize: 22 }}>⛔</span>
      <span>{validation.message}</span>
    </div>
  );
}
