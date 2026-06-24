// Step-by-step guide for driving the real camera through the Python bridge.
// Mirrors the README workflow so an operator can follow it from the dashboard.
export default function HowToUseCameraPanel({ workOrderId }) {
  const wo = workOrderId || "WO-1001";
  const steps = [
    "Start the backend (uvicorn on :8000).",
    "Start the frontend (npm run dev → :5173).",
    `Start the camera bridge: run_vision.py --show --post … --wo ${wo}.`,
    "Put a colored object inside a zone rectangle in the OpenCV window.",
    "Press p in the OpenCV window to post evidence.",
    "Click Verify Step here — Next Step unlocks if it passes.",
  ];
  return (
    <div className="panel">
      <h2>How to use the real camera</h2>
      <ol className="howto">
        {steps.map((s, i) => (
          <li key={i}>{s}</li>
        ))}
      </ol>
      <div className="meta" style={{ marginTop: 8 }}>
        The browser never opens the webcam — Python/OpenCV does, and posts the
        evidence to the backend.
      </div>
    </div>
  );
}
