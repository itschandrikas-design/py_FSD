
// Search patient by name
function searchPatient() {
    let input = document.getElementById("search").value.toLowerCase();

    let table = document.getElementById("patientTable");
    let rows = table.getElementsByTagName("tr");

    for (let i = 1; i < rows.length; i++) {
        let name = rows[i].getElementsByTagName("td")[1];

        if (name) {
            let text = name.textContent.toLowerCase();

            rows[i].style.display =
                text.includes(input) ? "" : "none";
        }
    }
}

// Confirm before deleting patient
function confirmDelete() {
    return confirm("Are you sure you want to delete this patient?");
}

// Display welcome message
function welcomeMessage() {
    alert("Welcome to Hospital Management System!");
}
