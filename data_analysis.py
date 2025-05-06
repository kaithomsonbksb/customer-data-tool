from flask import Flask, request, render_template, redirect, url_for
import pandas as pd
import matplotlib

matplotlib.use("Agg")  # Use a non-interactive backend
import matplotlib.pyplot as plt
from scipy.stats import linregress
import os

app = Flask(__name__)

# Global variable to store data
data = None


# Load the CSV file
def load_data(file_path):
    try:
        data = pd.read_csv(file_path)
        if "Date" not in data.columns or "PurchaseAmount" not in data.columns:
            raise ValueError("Required columns 'Date' or 'PurchaseAmount' are missing.")
        data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
        if data["Date"].isnull().any():
            raise ValueError("Invalid date format in the dataset.")
        return data
    except Exception as e:
        return str(e)


# Route for the homepage
@app.route("/", methods=["GET", "POST"])
def home():
    global data
    if request.method == "POST":
        file = request.files["file"]
        if file:
            file_path = os.path.join("uploads", file.filename)
            file.save(file_path)
            data = load_data(file_path)
            if isinstance(data, str):  # If an error occurred
                return render_template("index.html", error=data)
            return redirect(url_for("dashboard"))
    return render_template("index.html")


# Route for the dashboard
@app.route("/dashboard")
def dashboard():
    global data
    if data is None:
        return redirect(url_for("home"))
    return render_template("dashboard.html", data=data.head().to_html())


# Route to display statistics
@app.route("/statistics")
def statistics():
    global data
    if data is None:
        return redirect(url_for("home"))
    stats = data.describe().to_html()
    return render_template("statistics.html", stats=stats)


# Route to generate trend report
@app.route("/trend")
def trend():
    global data
    if data is None:
        return redirect(url_for("home"))

    try:
        # Ensure the Date column is properly converted to timestamps
        data["Timestamp"] = data["Date"].apply(lambda x: x.timestamp())
        x = data["Timestamp"]
        y = data["PurchaseAmount"]

        # Perform linear regression
        slope, intercept, r_value, p_value, std_err = linregress(x, y)
        data["Trend"] = intercept + slope * x

        # Generate the trend plot
        plt.figure(figsize=(10, 6))
        plt.scatter(
            data["Date"], data["PurchaseAmount"], label="Actual Data", color="blue"
        )
        plt.plot(data["Date"], data["Trend"], label="Trend Line", color="red")
        plt.title("Customer Purchase Trends Over Time")
        plt.xlabel("Date")
        plt.ylabel("Purchase Amount")
        plt.legend()
        plt.grid(True, linestyle="--", alpha=0.7)
        plt.savefig("static/trend.png")
        plt.close()  # Close the plot to free memory

        print("Trend plot generated successfully.")
        return render_template(
            "trend.html", slope=slope, intercept=intercept, r_squared=r_value**2
        )
    except Exception as e:
        print(f"Error in /trend route: {e}")
        return f"An error occurred while generating the trend report: {e}"


if __name__ == "__main__":
    app.run(debug=True)
