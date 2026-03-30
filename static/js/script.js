// ============================================================
// Expense Tracker – jQuery Interactions
// ============================================================

$(document).ready(function () {

    // ----------------------------------------------------------
    // 1. Auto-dismiss flash alerts after 4 seconds
    // ----------------------------------------------------------
    setTimeout(function () {
        $(".flash-alert").fadeOut("slow");
    }, 4000);


    // ----------------------------------------------------------
    // 2. Set default date to today on the Add Expense form
    // ----------------------------------------------------------
    var today = new Date().toISOString().split("T")[0];
    $("#date").val(today);


    // ----------------------------------------------------------
    // 3. Register form – password match validation
    // ----------------------------------------------------------
    $("#registerForm").on("submit", function (e) {
        var password = $("#password").val();
        var confirm  = $("#confirm_password").val();

        // Check minimum length
        if (password.length < 6) {
            e.preventDefault();
            alert("Password must be at least 6 characters.");
            return false;
        }

        // Check match
        if (password !== confirm) {
            e.preventDefault();
            alert("Passwords do not match.");
            return false;
        }
    });


    // ----------------------------------------------------------
    // 4. Add Expense form – field validation
    // ----------------------------------------------------------
    $("#expenseForm").on("submit", function (e) {
        var title    = $("#title").val().trim();
        var amount   = $("#amount").val();
        var category = $("#category").val();
        var date     = $("#date").val();

        // Check required fields
        if (!title || !amount || !category || !date) {
            e.preventDefault();
            alert("Please fill in all required fields.");
            return false;
        }

        // Check amount is a positive number
        if (isNaN(amount) || parseFloat(amount) <= 0) {
            e.preventDefault();
            alert("Please enter a valid positive amount.");
            return false;
        }
    });


    // ----------------------------------------------------------
    // 5. Budget form – validation
    // ----------------------------------------------------------
    $("#budgetForm").on("submit", function (e) {
        var budget = $("#budget").val();

        if (!budget || isNaN(budget) || parseFloat(budget) <= 0) {
            e.preventDefault();
            alert("Please enter a valid budget amount.");
            return false;
        }
    });


    // ----------------------------------------------------------
    // 6. Delete confirmation
    // ----------------------------------------------------------
    $(".delete-form").on("submit", function (e) {
        var confirmed = confirm("Are you sure you want to delete this expense?");
        if (!confirmed) {
            e.preventDefault();
        }
    });


    // ----------------------------------------------------------
    // 7. Login form – basic validation
    // ----------------------------------------------------------
    $("#loginForm").on("submit", function (e) {
        var email    = $("#email").val().trim();
        var password = $("#password").val();

        if (!email || !password) {
            e.preventDefault();
            alert("Please enter both email and password.");
            return false;
        }
    });

});
