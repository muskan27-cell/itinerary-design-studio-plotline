const trips = {
  sicily: {
    title: "Slow food route through Sicily",
    baseFee: 1250,
    days: [
      ["Palermo, unhurried", "Market breakfast, private chapel visit, aperitivo near the old port, and a late table held for caponata and natural Etna wines."],
      ["The inland table", "A driver-led route through olive groves, a family-run lunch, and an evening in a hill town with a one-page walking plot."],
      ["Volcanic ending", "Etna cellar tasting, lava-stone architecture notes, and a final seafood reservation timed around sunset."]
    ]
  },
  mexico: {
    title: "Architect's weekend in Mexico City",
    baseFee: 980,
    days: [
      ["Concrete and breakfast", "Luis Barragan context notes, a restrained breakfast counter, and a museum route that avoids the obvious queue patterns."],
      ["Neighborhood geometry", "Roma and Condesa by facade language, a design bookstore hold, mezcal tasting, and dinner in a courtyard room."],
      ["Water, stone, garden", "An early Xochimilco departure, UNAM mural stops, and a closing meal selected for material atmosphere."]
    ]
  },
  tokyo: {
    title: "Quiet design pilgrimage in Tokyo",
    baseFee: 1680,
    days: [
      ["Soft landing in Aoyama", "Ceramics, stationery, coffee pacing, and a dinner counter where the first night stays quiet."],
      ["Craft below the surface", "A maker studio visit, neighborhood bathhouse timing, and small-bar routing for a precise evening arc."],
      ["Edges of the city", "A coastal architecture day trip, train logistics, and a final omakase backup plan if weather changes the mood."]
    ]
  }
};

const persona = document.querySelector("#persona");
const pace = document.querySelector("#pace");
const concierge = document.querySelector("#concierge");
const title = document.querySelector("#itinerary-title");
const fee = document.querySelector("#fee");
const days = document.querySelector("#itinerary-days");
const supportChip = document.querySelector("#support-chip");
const briefForm = document.querySelector("#brief-form");
const formStatus = document.querySelector("#form-status");
const generatedPlan = document.querySelector("#generated-plan");
const loadDashboard = document.querySelector("#load-dashboard");
const metricGrid = document.querySelector("#metric-grid");
const briefList = document.querySelector("#brief-list");
const itineraryList = document.querySelector("#itinerary-list");
const conciergeList = document.querySelector("#concierge-list");
const conciergeForm = document.querySelector("#concierge-form");

function money(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0
  }).format(value);
}

function render() {
  const trip = trips[persona.value];
  const paceMultiplier = Number(pace.value);
  const conciergeFee = concierge.checked ? 450 : 0;
  const total = trip.baseFee + (paceMultiplier - 1) * 180 + conciergeFee;

  title.textContent = trip.title;
  fee.textContent = money(total);
  supportChip.hidden = !concierge.checked;

  const paceCopy = {
    1: "kept deliberately spacious",
    2: "layered with one optional detour",
    3: "filled with bookings and timed transitions"
  };

  days.innerHTML = trip.days
    .map(([heading, copy]) => {
      return `<li><div><strong>${heading}</strong><p>${copy} The day is ${paceCopy[pace.value]}.</p></div></li>`;
    })
    .join("");
}

function dayCard(day) {
  return `<li><strong>Day ${day.day}: ${day.title}</strong><p>${day.afternoon || day.notes}</p></li>`;
}

function renderGeneratedPlan(result) {
  if (!generatedPlan || !result.itinerary) return;
  const itinerary = result.itinerary;
  const payment = result.payment;
  generatedPlan.hidden = false;
  generatedPlan.innerHTML = `
    <p class="eyebrow">Generated first draft</p>
    <h3>${itinerary.title}</h3>
    <p>${itinerary.character} · ${itinerary.destination}</p>
    <ol>${itinerary.days.map(dayCard).join("")}</ol>
    <div class="plan-actions">
      <a class="button primary" href="/api/itineraries/${itinerary.id}/export" target="_blank" rel="noreferrer">Open PDF-style export</a>
      <a class="button secondary dark" href="${payment.checkout_url}">Mock checkout ${money(payment.amount)}</a>
    </div>
  `;
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Request failed");
  }
  return payload;
}

function record(html) {
  return `<article class="record">${html}</article>`;
}

function renderDashboard(data) {
  metricGrid.innerHTML = Object.entries(data.metrics)
    .map(([label, value]) => `<article><span>${value}</span><p>${label.replaceAll("_", " ")}</p></article>`)
    .join("");

  briefList.innerHTML = data.briefs
    .map((brief) =>
      record(`
        <strong>${brief.mood}</strong>
        <p>${brief.travel_window} · ${brief.tier} · ${brief.status}</p>
        <code>${brief.id}</code>
      `)
    )
    .join("");

  itineraryList.innerHTML = data.itineraries
    .map((itinerary) =>
      record(`
        <strong>${itinerary.title}</strong>
        <p>${itinerary.destination} · ${itinerary.web_status}</p>
        <a href="/api/itineraries/${itinerary.id}/export" target="_blank" rel="noreferrer">Export designed itinerary</a>
      `)
    )
    .join("");

  conciergeList.innerHTML = data.concierge_requests
    .map((item) =>
      record(`
        <strong>${item.urgency}</strong>
        <p>${item.request}</p>
        <code>${item.brief_id}</code>
      `)
    )
    .join("");
}

[persona, pace, concierge].forEach((control) => control.addEventListener("input", render));

render();

if (briefForm) {
  briefForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const submitButton = briefForm.querySelector("button[type='submit']");
    const formData = new FormData(briefForm);
    const payload = {
      mood: formData.get("mood"),
      travel_window: formData.get("travel_window"),
      tier: formData.get("tier"),
      traveler_email: formData.get("traveler_email")
    };

    formStatus.textContent = "Creating your brief...";
    formStatus.dataset.state = "loading";
    submitButton.disabled = true;

    try {
      const response = await fetch("/api/briefs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || "Could not create brief");
      }

      formStatus.textContent = `Brief ${result.brief.id} created. Generated itinerary ready. Estimated planning fee: ${money(result.brief.estimated_fee)}.`;
      formStatus.dataset.state = "success";
      renderGeneratedPlan(result);
      briefForm.reset();
    } catch (error) {
      formStatus.textContent = error.message;
      formStatus.dataset.state = "error";
    } finally {
      submitButton.disabled = false;
    }
  });
}

if (loadDashboard) {
  loadDashboard.addEventListener("click", async () => {
    loadDashboard.disabled = true;
    loadDashboard.textContent = "Loading...";
    try {
      const data = await fetchJson("/api/admin/dashboard", {
        headers: { Authorization: "Bearer dev-admin-token" }
      });
      renderDashboard(data);
    } catch (error) {
      metricGrid.innerHTML = `<article class="record error">${error.message}</article>`;
    } finally {
      loadDashboard.disabled = false;
      loadDashboard.textContent = "Refresh planner dashboard";
    }
  });
}

if (conciergeForm) {
  conciergeForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(conciergeForm);
    try {
      await fetchJson("/api/concierge/requests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          brief_id: formData.get("brief_id"),
          urgency: formData.get("urgency"),
          request: formData.get("request")
        })
      });
      conciergeForm.reset();
      loadDashboard?.click();
    } catch (error) {
      conciergeList.innerHTML = record(`<strong>${error.message}</strong>`);
    }
  });
}
