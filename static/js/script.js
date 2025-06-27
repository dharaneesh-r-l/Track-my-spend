// Update date-time every second in header
function updateDateTime() {
  const dt = new Date();
  const options = { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute:'2-digit', second:'2-digit' };
  const dtElem = document.getElementById('date-time');
  if (dtElem) {
    dtElem.textContent = dt.toLocaleString('en-IN', options);
  }
}
setInterval(updateDateTime, 1000);
updateDateTime();
