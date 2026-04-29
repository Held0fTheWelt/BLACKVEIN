/**
 * Phase 5: Narrator Streaming Frontend Tests
 *
 * Tests EventSource streaming, typewriter effect, input-UI blocking,
 * and ruhepunkt signal handling.
 */

describe("Play Narrative Stream Integration", () => {
  let shell;
  let narratorStreamer;

  beforeEach(() => {
    // Create play-shell DOM structure
    document.body.innerHTML = `
      <div class="play-shell" data-session-id="test_session">
        <div class="play-story-output"></div>
        <form class="play-input-form">
          <textarea class="play-input-text" name="player_input"></textarea>
          <button class="play-submit-button" type="submit">Submit</button>
        </form>
        <div class="play-narrator-indicator" hidden></div>
        <div class="play-ruhepunkt-signal" hidden></div>
      </div>
    `;

    shell = document.querySelector(".play-shell");
    narratorStreamer = window.NarrativeStreamer;
  });

  afterEach(() => {
    if (narratorStreamer && narratorStreamer.closeStream) {
      narratorStreamer.closeStream();
    }
    document.body.innerHTML = "";
  });

  describe("EventSource Streaming", () => {
    it("creates EventSource with correct endpoint", () => {
      const createEventSourceSpy = spyOn(window, "EventSource").and.returnValue({
        close: jasmine.createSpy("close"),
      });

      narratorStreamer.startStreaming("test_session");

      expect(createEventSourceSpy).toHaveBeenCalledWith(
        "/api/story/sessions/test_session/stream-narrator"
      );
    });

    it("handles narrator block events", () => {
      const mockEventSource = {
        close: jasmine.createSpy("close"),
        onmessage: null,
        onerror: null,
      };

      spyOn(window, "EventSource").and.returnValue(mockEventSource);
      narratorStreamer.startStreaming("test_session");

      const narratorBlockEvent = new MessageEvent("message", {
        data: JSON.stringify({
          event_id: "evt-1",
          event_kind: "narrator_block",
          data: {
            narrator_block: {
              narrator_text: "The tension builds.",
              atmospheric_tone: "mounting_pressure",
            },
          },
        }),
      });

      mockEventSource.onmessage(narratorBlockEvent);

      const storyOutput = document.querySelector(".play-story-output");
      expect(storyOutput.querySelector(".play-narrator-text")).toBeTruthy();
    });

    it("closes stream on error", () => {
      const mockEventSource = {
        close: jasmine.createSpy("close"),
        onmessage: null,
        onerror: null,
      };

      spyOn(window, "EventSource").and.returnValue(mockEventSource);
      narratorStreamer.startStreaming("test_session");

      mockEventSource.onerror();

      expect(mockEventSource.close).toHaveBeenCalled();
    });
  });

  describe("Narrator Block Rendering", () => {
    it("renders narrator block with text", () => {
      const mockEventSource = {
        close: jasmine.createSpy("close"),
        onmessage: null,
        onerror: null,
      };

      spyOn(window, "EventSource").and.returnValue(mockEventSource);
      narratorStreamer.startStreaming("test_session");

      const event = new MessageEvent("message", {
        data: JSON.stringify({
          event_id: "evt-1",
          event_kind: "narrator_block",
          data: {
            narrator_block: {
              narrator_text: "You feel the weight of silence.",
              atmospheric_tone: "simmering_conflict",
            },
          },
        }),
      });

      mockEventSource.onmessage(event);

      const narratorCard = document.querySelector(".play-turn-card--narrator");
      expect(narratorCard).toBeTruthy();
      expect(narratorCard.textContent).toContain("Narrator");
    });

    it("respects reduced motion preference for typewriter", (done) => {
      // Mock reduced motion
      spyOn(window, "matchMedia").and.returnValue({
        matches: true,
      });

      const mockEventSource = {
        close: jasmine.createSpy("close"),
        onmessage: null,
        onerror: null,
      };

      spyOn(window, "EventSource").and.returnValue(mockEventSource);
      narratorStreamer.startStreaming("test_session");

      const event = new MessageEvent("message", {
        data: JSON.stringify({
          event_id: "evt-1",
          event_kind: "narrator_block",
          data: {
            narrator_block: {
              narrator_text: "Quick text display",
            },
          },
        }),
      });

      mockEventSource.onmessage(event);

      setTimeout(() => {
        const textElement = document.querySelector(".play-narrator-text");
        // With reduced motion, text should be set immediately
        expect(textElement.textContent).toContain("Quick text display");
        done();
      }, 50);
    });
  });

  describe("Input-UI Blocking", () => {
    it("disables input fields when streaming starts", () => {
      const mockEventSource = {
        close: jasmine.createSpy("close"),
        onmessage: null,
        onerror: null,
      };

      spyOn(window, "EventSource").and.returnValue(mockEventSource);
      narratorStreamer.startStreaming("test_session");

      const inputField = document.querySelector(".play-input-text");
      const submitButton = document.querySelector(".play-submit-button");

      expect(inputField.disabled).toBe(true);
      expect(submitButton.disabled).toBe(true);
    });

    it("shows narrator indicator when streaming", () => {
      const mockEventSource = {
        close: jasmine.createSpy("close"),
        onmessage: null,
        onerror: null,
      };

      spyOn(window, "EventSource").and.returnValue(mockEventSource);
      narratorStreamer.startStreaming("test_session");

      const indicator = document.querySelector(".play-narrator-indicator");
      expect(indicator.hidden).toBe(false);
      expect(indicator.textContent).toContain("Narrator is speaking");
    });

    it("enables input when streaming stops", () => {
      const mockEventSource = {
        close: jasmine.createSpy("close"),
        onmessage: null,
        onerror: null,
      };

      spyOn(window, "EventSource").and.returnValue(mockEventSource);
      narratorStreamer.startStreaming("test_session");

      narratorStreamer.closeStream();

      const inputField = document.querySelector(".play-input-text");
      const submitButton = document.querySelector(".play-submit-button");

      expect(inputField.disabled).toBe(false);
      expect(submitButton.disabled).toBe(false);
    });
  });

  describe("Ruhepunkt Signal Handling", () => {
    it("handles ruhepunkt_reached event", () => {
      const mockEventSource = {
        close: jasmine.createSpy("close"),
        onmessage: null,
        onerror: null,
      };

      spyOn(window, "EventSource").and.returnValue(mockEventSource);
      narratorStreamer.startStreaming("test_session");

      const ruhepunktEvent = new MessageEvent("message", {
        data: JSON.stringify({
          event_id: "evt-ruhepunkt",
          event_kind: "ruhepunkt_reached",
          data: {
            ruhepunkt_reached: true,
          },
        }),
      });

      mockEventSource.onmessage(ruhepunktEvent);

      const inputField = document.querySelector(".play-input-text");
      expect(inputField.disabled).toBe(false);
    });

    it("shows ruhepunkt signal briefly", (done) => {
      jasmine.clock().install();

      const mockEventSource = {
        close: jasmine.createSpy("close"),
        onmessage: null,
        onerror: null,
      };

      spyOn(window, "EventSource").and.returnValue(mockEventSource);
      narratorStreamer.startStreaming("test_session");

      const ruhepunktEvent = new MessageEvent("message", {
        data: JSON.stringify({
          event_id: "evt-ruhepunkt",
          event_kind: "ruhepunkt_reached",
          data: {
            ruhepunkt_reached: true,
          },
        }),
      });

      mockEventSource.onmessage(ruhepunktEvent);

      const signal = document.querySelector(".play-ruhepunkt-signal");
      expect(signal.hidden).toBe(false);

      jasmine.clock().tick(3001);

      expect(signal.hidden).toBe(true);
      jasmine.clock().uninstall();
      done();
    });
  });

  describe("Streaming State", () => {
    it("tracks streaming state", () => {
      const mockEventSource = {
        close: jasmine.createSpy("close"),
        onmessage: null,
        onerror: null,
      };

      spyOn(window, "EventSource").and.returnValue(mockEventSource);

      let state = narratorStreamer.getState();
      expect(state.streaming).toBe(false);

      narratorStreamer.startStreaming("test_session");
      state = narratorStreamer.getState();
      expect(state.streaming).toBe(true);
      expect(state.currentSession).toBe("test_session");

      narratorStreamer.closeStream();
      state = narratorStreamer.getState();
      expect(state.streaming).toBe(false);
    });

    it("collects narrator blocks", () => {
      const mockEventSource = {
        close: jasmine.createSpy("close"),
        onmessage: null,
        onerror: null,
      };

      spyOn(window, "EventSource").and.returnValue(mockEventSource);
      narratorStreamer.startStreaming("test_session");

      const event1 = new MessageEvent("message", {
        data: JSON.stringify({
          event_id: "evt-1",
          event_kind: "narrator_block",
          data: { narrator_block: { narrator_text: "Block 1" } },
        }),
      });

      const event2 = new MessageEvent("message", {
        data: JSON.stringify({
          event_id: "evt-2",
          event_kind: "narrator_block",
          data: { narrator_block: { narrator_text: "Block 2" } },
        }),
      });

      mockEventSource.onmessage(event1);
      mockEventSource.onmessage(event2);

      const state = narratorStreamer.getState();
      expect(state.blocks.length).toBe(2);
      expect(state.blocks[0].event_id).toBe("evt-1");
      expect(state.blocks[1].event_id).toBe("evt-2");
    });
  });

  describe("Error Handling", () => {
    it("handles invalid JSON in events", () => {
      const mockEventSource = {
        close: jasmine.createSpy("close"),
        onmessage: null,
        onerror: null,
      };

      spyOn(window, "EventSource").and.returnValue(mockEventSource);
      spyOn(console, "error");

      narratorStreamer.startStreaming("test_session");

      const invalidEvent = new MessageEvent("message", {
        data: "not valid json",
      });

      mockEventSource.onmessage(invalidEvent);

      expect(console.error).toHaveBeenCalled();
    });

    it("handles narrator error events", () => {
      const mockEventSource = {
        close: jasmine.createSpy("close"),
        onmessage: null,
        onerror: null,
      };

      spyOn(window, "EventSource").and.returnValue(mockEventSource);
      spyOn(console, "error");

      narratorStreamer.startStreaming("test_session");

      const errorEvent = new MessageEvent("message", {
        data: JSON.stringify({
          error: "streaming_failed",
          message: "Test error",
        }),
      });

      mockEventSource.onmessage(errorEvent);

      expect(console.error).toHaveBeenCalledWith(
        "Narrator streaming error:",
        "streaming_failed",
        "Test error"
      );
      expect(mockEventSource.close).toHaveBeenCalled();
    });
  });
});

describe("MVP3 Phase 5 Gate", () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div class="play-shell" data-session-id="test_session">
        <div class="play-story-output"></div>
        <form class="play-input-form">
          <textarea class="play-input-text" name="player_input"></textarea>
          <button class="play-submit-button" type="submit">Submit</button>
        </form>
        <div class="play-narrator-indicator" hidden></div>
        <div class="play-ruhepunkt-signal" hidden></div>
      </div>
    `;
  });

  afterEach(() => {
    if (window.NarrativeStreamer && window.NarrativeStreamer.closeStream) {
      window.NarrativeStreamer.closeStream();
    }
    document.body.innerHTML = "";
  });

  it("Gate: Frontend receives narrator blocks via EventSource", () => {
    const mockEventSource = {
      close: jasmine.createSpy("close"),
      onmessage: null,
      onerror: null,
    };

    spyOn(window, "EventSource").and.returnValue(mockEventSource);

    window.NarrativeStreamer.startStreaming("test_session");

    const event = new MessageEvent("message", {
      data: JSON.stringify({
        event_id: "evt-1",
        event_kind: "narrator_block",
        data: {
          narrator_block: {
            narrator_text: "The narrator speaks.",
          },
        },
      }),
    });

    mockEventSource.onmessage(event);

    const narratorCard = document.querySelector(".play-turn-card--narrator");
    expect(narratorCard).toBeTruthy();
  });

  it("Gate: Frontend blocks input-UI during narrator streaming", () => {
    const mockEventSource = {
      close: jasmine.createSpy("close"),
      onmessage: null,
      onerror: null,
    };

    spyOn(window, "EventSource").and.returnValue(mockEventSource);

    window.NarrativeStreamer.startStreaming("test_session");

    const inputField = document.querySelector(".play-input-text");
    const submitButton = document.querySelector(".play-submit-button");

    expect(inputField.disabled).toBe(true);
    expect(submitButton.disabled).toBe(true);
  });

  it("Gate: Frontend enables input after ruhepunkt signal", () => {
    const mockEventSource = {
      close: jasmine.createSpy("close"),
      onmessage: null,
      onerror: null,
    };

    spyOn(window, "EventSource").and.returnValue(mockEventSource);

    window.NarrativeStreamer.startStreaming("test_session");

    const ruhepunktEvent = new MessageEvent("message", {
      data: JSON.stringify({
        event_id: "evt-ruhepunkt",
        event_kind: "ruhepunkt_reached",
        data: { ruhepunkt_reached: true },
      }),
    });

    mockEventSource.onmessage(ruhepunktEvent);

    const inputField = document.querySelector(".play-input-text");
    expect(inputField.disabled).toBe(false);
  });
});
