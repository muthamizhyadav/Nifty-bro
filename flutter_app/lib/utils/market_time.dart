/// NSE market time helpers — always show IST on charts regardless of phone timezone.
class MarketTime {
  static const _istOffset = Duration(hours: 5, minutes: 30);

  static int epochSeconds(int time) =>
      time > 9999999999 ? time ~/ 1000 : time;

  static DateTime istFromEpoch(int time) {
    final sec = epochSeconds(time);
    return DateTime.fromMillisecondsSinceEpoch(sec * 1000, isUtc: true)
        .add(_istOffset);
  }

  static bool sameCandleBucket(int t1, int t2, {int minutes = 15}) {
    final a = istFromEpoch(t1);
    final b = istFromEpoch(t2);
    if (a.year != b.year || a.month != b.month || a.day != b.day) return false;
    if (minutes == 15) {
      const openMin = 9 * 60 + 15;
      final ma = a.hour * 60 + a.minute;
      final mb = b.hour * 60 + b.minute;
      if (ma >= openMin && mb >= openMin) {
        return (ma - openMin) ~/ 15 == (mb - openMin) ~/ 15;
      }
    }
    return a.hour == b.hour && (a.minute ~/ minutes) == (b.minute ~/ minutes);
  }
}
