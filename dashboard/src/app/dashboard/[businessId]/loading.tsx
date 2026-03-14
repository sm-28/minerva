export default function DashboardLoading() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-x-0 top-0 z-[80]"
    >
      <div className="top-progress-track">
        <div className="top-progress-bar" />
      </div>
    </div>
  );
}
