export function buildDateRangeFromHours(
  hoursBack: number,
): { startTime: string; endTime: string } {
  const now = new Date();

  const endTime = now.toISOString().slice(0, 10);

  const start = new Date(now.getTime() - hoursBack * 60 * 60 * 1000);
  const startTime = start.toISOString().slice(0, 10);

  return { startTime, endTime };
}