(function () {
  "use strict";
  var months = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"];
  var weekdays = ["ش", "ی", "د", "س", "چ", "پ", "ج"];
  var digits = "۰۱۲۳۴۵۶۷۸۹";
  function fa(value) { return String(value).replace(/\d/g, function (d) { return digits[Number(d)]; }); }
  function normalize(value) { return String(value || "").replace(/[۰-۹٠-٩]/g, function (d) { var i = digits.indexOf(d); return i < 0 ? "٠١٢٣٤٥٦٧٨٩".indexOf(d) : i; }); }
  function days(year, month) { return month < 7 ? 31 : month < 12 ? 30 : ((year + 1) % 33 < 8 ? 30 : 29); }
  function parse(value) { var match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(normalize(value)); return match ? { year: +match[1], month: +match[2], day: +match[3] } : null; }
  function today() {
    var parts = new Intl.DateTimeFormat("en-US-u-ca-persian", { year: "numeric", month: "numeric", day: "numeric" }).formatToParts(new Date());
    var value = {};
    parts.forEach(function (part) { if (part.type !== "literal") value[part.type] = +normalize(part.value); });
    return { year: value.year, month: value.month, day: value.day };
  }
  function attach(input) {
    var state = parse(input.value) || today();
    var picker = document.createElement("div"); picker.className = "jalali-suite-datepicker"; picker.hidden = true; document.body.appendChild(picker);
    function render() {
      var html = '<header><button type="button" data-step="-1" aria-label="ماه قبل">&lt;</button><strong>' + months[state.month - 1] + " " + fa(state.year) + '</strong><button type="button" data-step="1" aria-label="ماه بعد">&gt;</button></header><div class="week">' + weekdays.map(function (d) { return "<span>" + d + "</span>"; }).join("") + '</div><div class="days">';
      for (var day = 1; day <= days(state.year, state.month); day++) html += '<button type="button" data-day="' + day + '">' + fa(day) + "</button>";
      picker.innerHTML = html + "</div>";
    }
    function position() { var rect = input.getBoundingClientRect(); picker.style.left = (window.scrollX + rect.left) + "px"; picker.style.top = (window.scrollY + rect.bottom + 4) + "px"; }
    input.addEventListener("focus", function () { picker.hidden = false; position(); render(); });
    picker.addEventListener("click", function (event) {
      var step = event.target.getAttribute("data-step"), day = event.target.getAttribute("data-day");
      if (step) { state.month += +step; if (state.month === 0) { state.month = 12; state.year--; } if (state.month === 13) { state.month = 1; state.year++; } render(); }
      if (day) { state.day = +day; input.value = fa(state.year.toString().padStart(4, "0") + "-" + state.month.toString().padStart(2, "0") + "-" + state.day.toString().padStart(2, "0")); input.dispatchEvent(new Event("change", { bubbles: true })); picker.hidden = true; }
    });
    document.addEventListener("click", function (event) { if (event.target !== input && !picker.contains(event.target)) picker.hidden = true; });
  }
  document.addEventListener("DOMContentLoaded", function () { document.querySelectorAll("input[data-jalali-datepicker]").forEach(attach); });
}());