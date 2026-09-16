(function () {
  "use strict";
  var months = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"];
  var weekdays = ["ش", "ی", "د", "س", "چ", "پ", "ج"];
  var digits = "۰۱۲۳۴۵۶۷۸۹";
  function fa(value) { return String(value).replace(/\d/g, function (digit) { return digits[Number(digit)]; }); }
  function normalize(value) { return String(value || "").replace(/[۰-۹٠-٩]/g, function (digit) { var i = digits.indexOf(digit); return i < 0 ? "٠١٢٣٤٥٦٧٨٩".indexOf(digit) : i; }); }
  function days(year, month) { return month < 7 ? 31 : month < 12 ? 30 : ((year + 1) % 33 < 8 ? 30 : 29); }
  function parse(value) { var match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(normalize(value)); return match ? { year: +match[1], month: +match[2], day: +match[3] } : null; }
  function format(value) { return value.year.toString().padStart(4, "0") + "-" + value.month.toString().padStart(2, "0") + "-" + value.day.toString().padStart(2, "0"); }
  function sameDate(left, right) { return left && right && left.year === right.year && left.month === right.month && left.day === right.day; }
  function today() {
    var parts = new Intl.DateTimeFormat("en-US-u-ca-persian", { year: "numeric", month: "numeric", day: "numeric" }).formatToParts(new Date());
    var value = {};
    parts.forEach(function (part) { if (part.type !== "literal") value[part.type] = +normalize(part.value); });
    return { year: value.year, month: value.month, day: value.day };
  }
  // Farvardin 1, 1403 was Wednesday. This uses the same lightweight leap-year
  // rule as days() to align the first day of each visible month.
  function weekday(year, month, day) {
    var cursor, offset = day - 1;
    if (year >= 1403) for (cursor = 1403; cursor < year; cursor++) offset += days(cursor, 12);
    else for (cursor = year; cursor < 1403; cursor++) offset -= days(cursor, 12);
    for (cursor = 1; cursor < month; cursor++) offset += days(year, cursor);
    return ((4 + offset) % 7 + 7) % 7;
  }
  function attach(input) {
    var selected = parse(input.value), current = today(), state = selected || current;
    var picker = document.createElement("div");
    picker.className = "jalali-suite-datepicker";
    picker.hidden = true;
    picker.dir = "rtl";
    document.body.appendChild(picker);
    function changeMonth(step) { state.month += step; if (state.month === 0) { state.month = 12; state.year--; } if (state.month === 13) { state.month = 1; state.year++; } }
    function render() {
      var day, leading = weekday(state.year, state.month, 1);
      var html = '<header class="jalali-suite-datepicker__header"><div class="jalali-suite-datepicker__control"><button type="button" data-year="-1" aria-label="سال قبل">−</button><strong>' + fa(state.year) + '</strong><button type="button" data-year="1" aria-label="سال بعد">+</button></div><div class="jalali-suite-datepicker__control"><button type="button" data-month="-1" aria-label="ماه قبل">−</button><strong>' + months[state.month - 1] + '</strong><button type="button" data-month="1" aria-label="ماه بعد">+</button></div></header><div class="jalali-suite-datepicker__week">' + weekdays.map(function (name) { return "<span>" + name + "</span>"; }).join("") + '</div><div class="jalali-suite-datepicker__days">';
      for (day = 0; day < leading; day++) html += '<span class="jalali-suite-datepicker__blank"></span>';
      for (day = 1; day <= days(state.year, state.month); day++) {
        var candidate = { year: state.year, month: state.month, day: day }, classes = "";
        if (sameDate(candidate, current)) classes += " is-today";
        if (sameDate(candidate, selected)) classes += " is-selected";
        html += '<button type="button" data-day="' + day + '" class="' + classes.trim() + '">' + fa(day) + "</button>";
      }
      picker.innerHTML = html + '</div><footer><button type="button" data-clear="true">خالی</button><button type="button" data-today="true">امروز</button></footer>';
    }
    function position() { var rect = input.getBoundingClientRect(); picker.style.left = (window.scrollX + rect.left) + "px"; picker.style.top = (window.scrollY + rect.bottom + 4) + "px"; }
    function open() { selected = parse(input.value); state = selected || today(); picker.hidden = false; position(); render(); }
    function setValue(value) { selected = value; input.value = value ? fa(format(value)) : ""; input.dispatchEvent(new Event("change", { bubbles: true })); picker.hidden = true; }
    input.addEventListener("focus", open);
    input.addEventListener("click", open);
    input.addEventListener("keydown", function (event) { if (event.key === "Escape") picker.hidden = true; });
    window.addEventListener("resize", function () { if (!picker.hidden) position(); });
    window.addEventListener("scroll", function () { if (!picker.hidden) position(); }, true);
    picker.addEventListener("click", function (event) {
      var target = event.target, day = target.getAttribute("data-day"), month = target.getAttribute("data-month"), year = target.getAttribute("data-year");
      if (month) { changeMonth(+month); render(); }
      else if (year) { state.year += +year; render(); }
      else if (day) setValue({ year: state.year, month: state.month, day: +day });
      else if (target.getAttribute("data-today")) setValue(today());
      else if (target.getAttribute("data-clear")) setValue(null);
    });
    document.addEventListener("click", function (event) { if (event.target !== input && !picker.contains(event.target)) picker.hidden = true; });
  }
  document.addEventListener("DOMContentLoaded", function () { document.querySelectorAll("input[data-jalali-datepicker]").forEach(attach); });
}());
