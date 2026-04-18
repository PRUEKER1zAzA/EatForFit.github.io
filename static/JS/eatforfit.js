function calculateCal() {
    let carb = parseFloat(document.getElementById("carb").value) || 0;
    let protein = parseFloat(document.getElementById("protein").value) || 0;
    let fat = parseFloat(document.getElementById("fat").value) || 0;
    let cal = document.getElementById("cal");
    cal.value = Math.round((carb * 4) + (protein * 4) + (fat * 9));
}

function cf() {
    calculateCal();
    return confirm("ยืนยันใช่หรือไม่");
}