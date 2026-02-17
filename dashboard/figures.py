from typing import Optional

import altair as alt

day_order = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def get_heatmap(df, road_name: Optional[str] = None):

    base = alt.Chart(df).encode(
        x=alt.X(
            "processed_day",
            sort=day_order,
            title="Day",
            # Rotate labels by -45 degrees
            axis=alt.Axis(labelAngle=-45, labelOverlap=False),
        ),
        y=alt.Y("processed_hour", title="Hour", sort="descending"),
    )

    # 2. Create the Heatmap (Rectangles)
    # We aggregate the mean speed automatically here.
    heatmap = base.mark_rect().encode(
        color=alt.Color(
            "weighted_avg_speed",
            aggregate="mean",
            scale=alt.Scale(scheme="redyellowgreen"),
            title="Speed",
        ),
        tooltip=[
            "processed_day",
            "processed_hour",
            alt.Tooltip("weighted_avg_speed", aggregate="mean", format=".2f"),
        ],
    )

    # 3. Create the Text Labels (equivalent to text_auto=True)
    text = base.mark_text().encode(
        text=alt.Text("weighted_avg_speed", aggregate="mean", format=".1f"),
        # Optional: Adjust text color based on background for readability
        # color=alt.value('black')
    )

    # 4. Combine and Display
    title = "Spatiotemporal Heatmap"
    if road_name:
        title += f" for {road_name}"
    chart = (heatmap + text).properties(title=title)

    return chart


def get_twin_plot(df, road_name: Optional[str] = None):

    base = alt.Chart(df).encode(
        x=alt.X(
            "processed_date:T", axis=alt.Axis(title="Date")
        )  # 'T' for encoding time data value
    )

    # 3. Create the First Line (Revenue - Left Axis)
    # We give it a specific color and title.
    line1 = base.mark_line(color="#57A44C").encode(
        y=alt.Y(
            "weighted_avg_speed",
            axis=alt.Axis(title="Weighted average speed (Km/h)", titleColor="#57A44C"),
            scale=alt.Scale(zero=False),  # Optional: allows axis to scale to data
        )
    )

    # 4. Create the Second Line (Growth Rate - Right Axis)
    # We use transform_calculus or simply distinct encoding to separate it.
    # The key is resolve_scale(y='independent') later.
    line2 = base.mark_line(
        color="#AC3E31", strokeDash=[5, 5]
    ).encode(  # Dashed line style
        y=alt.Y(
            "total_counted_cars",
            axis=alt.Axis(title="Total vehicles counted", titleColor="#AC3E31"),
            scale=alt.Scale(zero=False),
        )
    )

    # 5. Layer them together
    # This is the magic step: resolve_scale(y='independent')
    chart = (
        alt.layer(line1, line2)
        .resolve_scale(y="independent")
        .properties(title={"text": "Traffic Trends: Speed vs. Volume"})
        .interactive()
    )

    return chart


def get_bar_chart(df, road_name: Optional[str] = None):
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            # X-axis: The length of the bar (std_average_speed)
            x=alt.X(
                "std_average_speed",
                title="Standard deviation of the weighted average speed",
            ),
            # Y-axis: The categorical labels.
            # sort='-x' ensures the longest bars appear at the top.
            y=alt.Y("road_name", sort="-x", title="Road name"),
            # Color: The continuous scale based on weighted_avg_speed
            color=alt.Color(
                "weighted_avg_speed",
                scale=alt.Scale(scheme="redyellowgreen"),
                title="Speed",
            ),
            # Tooltip: Add hover info similar to Plotly
            tooltip=["road_name", "std_average_speed", "weighted_avg_speed"],
        )
    )

    return chart


def get_twin_multiple(df):
    # --- ALTAIR IMPLEMENTATION ---

    # 1. Create a selection for interactivity (Legacy Syntax)
    # In Altair 4, use 'selection_multi' instead of 'selection_point'
    highlight = alt.selection_multi(fields=["road_name"], bind="legend")

    # 2. Shared Base
    base = alt.Chart(df).encode(
        x=alt.X("processed_hour", axis=alt.Axis(title="Hour of Day", labelAngle=-45)),
        tooltip=[
            alt.Tooltip("road_name", title="Road"),
            alt.Tooltip("processed_hour", title="Hour"),
            alt.Tooltip("weighted_avg_speed", title="Speed (km/h)", format=".1f"),
            alt.Tooltip("avg_counted_cars", title="Volume (Count)", format=","),
        ],
    )

    # 3. Speed Line (Left Axis, Solid)
    # In Altair 4, use '.add_selection' instead of '.add_params'
    line_speed = (
        base.mark_line(strokeWidth=3)
        .encode(
            y=alt.Y(
                "weighted_avg_speed:Q",
                axis=alt.Axis(title="Weighted average speed (Km/h)"),
                scale=alt.Scale(zero=False),
            ),
            color=alt.Color(
                "road_name:N", legend=alt.Legend(title="Click to Isolate Road")
            ),
            opacity=alt.condition(highlight, alt.value(1), alt.value(0.1)),
        )
        .add_selection(highlight)
    )

    # 4. Volume Line (Right Axis, Dashed)
    line_volume = base.mark_line(strokeDash=[4, 4], strokeWidth=3).encode(
        y=alt.Y(
            "avg_counted_cars:Q",
            axis=alt.Axis(title="Average vehicle volume"),
            scale=alt.Scale(zero=False),
        ),
        color=alt.Color("road_name:N", legend=None),
        opacity=alt.condition(highlight, alt.value(1), alt.value(0.1)),
    )

    # 5. Layer and Final Polish
    chart = (
        alt.layer(line_speed, line_volume)
        .resolve_scale(y="independent")
        .properties(
            title={
                "text": "Solid Line = Speed (Left) | Dashed Line = Volume (Right)",
                "color": "gray",
            },
            height=400,
        )
    )

    return chart


def get_stacked_bars(df):

    chart = alt.Chart(df).transform_fold(
        ['dead_percent', 'missing_reading_percent'],
        as_=['Error Type', 'Percent']
    ).transform_calculate(
        # This creates a new field 'Label' with clean names
        Label="datum['Error Type'] === 'dead_percent' ? 'Dead Readings' : 'Missing Readings'"
    ).mark_bar().encode(
        x=alt.X('date:T', title='Date', axis=alt.Axis(format='%b %Y', labelAngle=-45)),
        y=alt.Y('Percent:Q', title='Percent of bad readings'),
        
        # Use the new 'Label' field for color
        color=alt.Color('Label:N', 
                        legend=alt.Legend(title="Error category"),
                        scale=alt.Scale(scheme='tableau10')),
        
        tooltip=[
            alt.Tooltip('date:T', title='Date', format='%B %Y'),
            alt.Tooltip('Label:N', title='Category'), # Use Label here too
            alt.Tooltip('Percent:Q', title='Percent', format='.3') # Format as percentage
        ]
    ).properties(
        width=700, height=500, title='Bad Data Readings by Type'
    ).interactive()
    
    return chart