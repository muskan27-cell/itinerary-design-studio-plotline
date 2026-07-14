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

      formStatus.textContent = `Brief ${result.brief.id} created. Estimated planning fee: ${money(result.brief.estimated_fee)}.`;
      formStatus.dataset.state = "success";
      briefForm.reset();
    } catch (error) {
      formStatus.textContent = error.message;
      formStatus.dataset.state = "error";
    } finally {
      submitButton.disabled = false;
    }
  });
}
