let totalCal = 0, totalP = 0, totalC = 0, totalF = 0;

function addFood() {
  const food = document.getElementById("food").value;
  const cal = Number(document.getElementById("cal").value);
  const p = Number(document.getElementById("protein").value);
  const c = Number(document.getElementById("carb").value);
  const f = Number(document.getElementById("fat").value);

  if (!food) return alert("กรอกชื่ออาหารก่อน");

  const row = `
    <tr>
      <td>${food}</td>
      <td>${cal}</td>
      <td>${p}</td>
      <td>${c}</td>
      <td>${f}</td>
    </tr>
  `;

  document.getElementById("list").innerHTML += row;

  totalCal += cal;
  totalP += p;
  totalC += c;
  totalF += f;

  document.getElementById("tCal").innerText = totalCal;
  document.getElementById("tProtein").innerText = totalP;
  document.getElementById("tCarb").innerText = totalC;
  document.getElementById("tFat").innerText = totalF;
}
