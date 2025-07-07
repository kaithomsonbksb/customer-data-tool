import re
import customtkinter
from tkinter import filedialog, messagebox
import pandas
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from scipy.stats import linregress


class DataAnalyzerApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Data Analysis Tool")
        self.data_frame = None
        self.setup_ui()

    def setup_ui(self):
        # Create a button row at the top
        buttons_frame = customtkinter.CTkFrame(self.root)
        buttons_frame.pack(fill="x", pady=10)
        self.upload_btn = customtkinter.CTkButton(
            buttons_frame, text="Upload CSV", command=self.pick_file
        )
        self.upload_btn.grid(row=0, column=0, padx=10, pady=0, sticky="e")
        self.modify_btn = customtkinter.CTkButton(
            buttons_frame, text="Edit Data", command=self.open_editor
        )
        self.modify_btn.grid(row=0, column=1, padx=10, pady=0, sticky="w")
        buttons_frame.grid_columnconfigure(0, weight=1)
        buttons_frame.grid_columnconfigure(1, weight=1)
        self.tabs = customtkinter.CTkTabview(self.root)  # Set up the tabs
        self.tabs.pack(expand=1, fill="both")
        self.tab_dashboard = self.tabs.add("Dashboard")
        self.dashboard_output = customtkinter.CTkTextbox(
            self.tab_dashboard, wrap="none", height=400, width=800
        )
        self.dashboard_output.pack(expand=1, fill="both")
        self.dashboard_output.insert("0.0", "Upload a CSV file to get started...\n")
        self.tab_stats = self.tabs.add("Statistics")
        self.tab_trend = self.tabs.add("Trend")
        self.trend_canvas = None
        self.trend_note = customtkinter.CTkLabel(self.tab_trend, text="")
        self.trend_note.pack()
        self.trend_button = customtkinter.CTkButton(
            self.tab_trend, text="Show Trend Plot", command=self.render_trend_plot
        )
        self.trend_button.pack(pady=5)

    def pick_file(self):
        file = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if not file:
            return
        try:
            df = pandas.read_csv(file)
            if (
                "Date" not in df.columns or "PurchaseAmount" not in df.columns
            ):  # sanity check for required columns
                raise ValueError(
                    "Missing columns: Expecting 'Date' and 'PurchaseAmount'."
                )
            df["Date"] = pandas.to_datetime(df["Date"], errors="coerce")
            if df["Date"].isnull().any():
                raise ValueError("Some dates couldn't be parsed properly.")
            self.data_frame = df
            self.update_dashboard()
            self.update_stats()
            self.trend_note.configure(text="")
            if self.trend_canvas:  # is theres an old canvas, get rid of it
                self.trend_canvas.get_tk_widget().pack_forget()
        except Exception as err:
            messagebox.showerror("Oops", f"Couldn't load the file:\n{err}")

    def update_dashboard(self):
        self.dashboard_output.delete("0.0", customtkinter.END)
        if self.data_frame is not None:
            self.dashboard_output.insert(
                customtkinter.END, self.data_frame.to_string(index=False)
            )
        else:
            self.dashboard_output.insert(customtkinter.END, "Still waiting on a CSV...")

    def update_stats(self):
        for widget in self.tab_stats.winfo_children():
            widget.destroy()
        if self.data_frame is not None:
            desc = self.data_frame.describe(include="all")
            for col in desc.columns:  # handle Date separately
                if col == "Date":
                    for idx in desc.index:
                        if idx not in ["count", "min", "max"]:
                            desc.at[idx, col] = ""
                        elif idx in ["min", "max"]:
                            desc.at[idx, col] = str(desc.at[idx, col])
                elif pandas.api.types.is_numeric_dtype(desc[col]):
                    desc[col] = desc[col].apply(
                        lambda val: f"{val:.2f}" if pandas.notnull(val) else ""
                    )
            headers = ["Stat"] + list(desc.columns)
            rows = list(desc.index)
            for i, head in enumerate(headers):  # create header labels
                customtkinter.CTkLabel(
                    self.tab_stats, text=head, font=("Arial", 12, "bold")
                ).grid(row=0, column=i, padx=5, pady=2, sticky="nsew")
            for r_idx, stat in enumerate(rows, start=1):  # create table body
                customtkinter.CTkLabel(
                    self.tab_stats, text=stat, font=("Arial", 12)
                ).grid(row=r_idx, column=0, padx=5, pady=2, sticky="nsew")
                for c_idx, col in enumerate(desc.columns, start=1):
                    val = desc.at[stat, col]
                    customtkinter.CTkLabel(
                        self.tab_stats, text=val, font=("Arial", 12)
                    ).grid(row=r_idx, column=c_idx, padx=5, pady=2, sticky="nsew")
            for i in range(len(headers)):  # stretch grid to fill
                self.tab_stats.grid_columnconfigure(i, weight=1)
            for i in range(len(rows) + 1):
                self.tab_stats.grid_rowconfigure(i, weight=1)
        else:
            customtkinter.CTkLabel(self.tab_stats, text="No data loaded yet.").pack(
                expand=1, fill="both"
            )

    def open_editor(self):
        if self.data_frame is None:
            messagebox.showinfo("Wait", "Please upload a CSV before editing.")
            return
        editor = customtkinter.CTkToplevel(self.root)
        editor.title("Edit Data")
        editor.geometry("550x500")
        edit_panel = customtkinter.CTkFrame(editor)
        edit_panel.pack(padx=10, pady=10, fill="both", expand=True)
        cols = list(self.data_frame.columns)
        row_widgets = []
        customtkinter.CTkLabel(
            edit_panel, text="Edit Data Table", font=("Arial", 14, "bold")
        ).grid(row=0, column=0, columnspan=len(cols), pady=(0, 10))
        for c_idx, name in enumerate(cols):
            customtkinter.CTkLabel(
                edit_panel, text=name, font=("Arial", 12, "bold")
            ).grid(row=1, column=c_idx, padx=5, pady=2)
        for r_idx, data_row in enumerate(
            self.data_frame.itertuples(index=False), start=2
        ):
            entries = []
            for c_idx, val in enumerate(data_row):
                ent = customtkinter.CTkEntry(edit_panel, width=120)
                ent.insert(0, str(val))
                ent.grid(row=r_idx, column=c_idx, padx=2, pady=2)
                entries.append(ent)
            row_widgets.append(entries)

        def commit_changes():
            updated_rows = []
            for widgets in row_widgets:
                current_row = []
                for i, widget in enumerate(widgets):
                    val = widget.get()
                    colname = cols[i]
                    if colname == "Date":
                        if not re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", val):
                            messagebox.showerror(
                                "Format Error",
                                f"Date must be in full timestamp format. Got: {val}",
                            )
                            return
                    else:
                        try:
                            float(val)  # Checking if it's a number
                        except ValueError:
                            messagebox.showerror(
                                "Bad Input",
                                f"Non-date fields must be numbers. Got: {val}",
                            )
                            return
                    current_row.append(val)
                updated_rows.append(current_row)
            self.data_frame = pandas.DataFrame(updated_rows, columns=cols)
            messagebox.showinfo("Saved", "Changes saved successfully!")
            editor.destroy()
            self.update_dashboard()
            self.update_stats()

        customtkinter.CTkButton(
            edit_panel, text="Save Changes", command=commit_changes
        ).grid(row=len(row_widgets) + 2, column=0, columnspan=len(cols), pady=10)

    def render_trend_plot(self):
        if self.data_frame is None:
            messagebox.showinfo("Missing Data", "Please upload some data first.")
            return

        try:
            x_vals = pandas.to_datetime(self.data_frame["Date"]).map(
                pandas.Timestamp.toordinal
            )
            y_vals = self.data_frame["PurchaseAmount"]

            slope, intercept, r_val, _, _ = linregress(x_vals, y_vals)
            self.data_frame["Trend"] = intercept + slope * x_vals

            matplotlib.pyplot.figure(figsize=(8, 5))
            matplotlib.pyplot.scatter(
                self.data_frame["Date"],
                self.data_frame["PurchaseAmount"],
                label="Actual",
                color="blue",
            )
            matplotlib.pyplot.plot(
                self.data_frame["Date"],
                self.data_frame["Trend"],
                label="Trend",
                color="red",
            )

            matplotlib.pyplot.title("Customer Purchase Trends")
            matplotlib.pyplot.xlabel("Date")
            matplotlib.pyplot.ylabel("Amount Spent")
            matplotlib.pyplot.grid(True, linestyle="--", alpha=0.7)
            matplotlib.pyplot.legend()

            chart = matplotlib.pyplot.gcf()
            if self.trend_canvas:
                self.trend_canvas.get_tk_widget().pack_forget()

            self.trend_canvas = FigureCanvasTkAgg(chart, master=self.tab_trend)
            self.trend_canvas.draw()
            self.trend_canvas.get_tk_widget().pack(expand=1, fill="both")

            self.trend_note.configure(
                text=f"Slope: {slope:.2f}, Intercept: {intercept:.2f}, R²: {r_val**2:.2f}"
            )
            matplotlib.pyplot.close()

        except Exception as boom:
            messagebox.showerror(
                "Error", f"Something went wrong while plotting:\n{boom}"
            )


if __name__ == "__main__":
    customtkinter.set_appearance_mode("system")
    customtkinter.set_default_color_theme("blue")
    root_window = customtkinter.CTk()
    root_window.state("zoomed")
    app = DataAnalyzerApp(root_window)
    root_window.mainloop()


# sort out stats
# correct formating for dates
# correct text size and proportions
