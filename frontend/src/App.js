import React, { useState, useEffect } from "react";
import "./App.css";
import { postJSON, getJSON, postFile } from "./api";

function App() {
  const [activeTab, setActiveTab] = useState("pdf");
  const [notes, setNotes] = useState([]);
  const [noteTitle, setNoteTitle] = useState("");
  const [noteContent, setNoteContent] = useState("");
  const [schedules, setSchedules] = useState([]);
  const [summaries, setSummaries] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [copilotResponse, setCopilotResponse] = useState("");
  const [online, setOnline] = useState(navigator.onLine);

  // Monitor online/offline
  useEffect(() => {
    const handleOnline = () => setOnline(true);
    const handleOffline = () => setOnline(false);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  // Load initial data
  useEffect(() => {
    async function loadData() {
      try {
        const notesData = await getJSON("/api/notes");
        setNotes(notesData);

        const schedulesData = await getJSON("/api/schedule");
        setSchedules(schedulesData);

        const summariesData = await getJSON("/api/summaries");
        setSummaries(summariesData);
      } catch (err) {
        console.error("Error loading data", err);
      }
    }
    loadData();
  }, []);

  // Notes
  async function createNote() {
    if (!noteTitle || !noteContent) return;
    const newNote = await postJSON("/api/notes", {
      title: noteTitle,
      content: noteContent
    });
    setNotes([...notes, newNote]);
    setNoteTitle("");
    setNoteContent("");
  }

  // Schedules
  async function createSchedule() {
    const newSchedule = await postJSON("/api/schedule", {
      title: "Test Reminder",
      description: "This is a reminder",
      scheduled_time: new Date().toISOString(),
      notification_type: "reminder"
    });
    setSchedules([...schedules, newSchedule]);
  }

  // Summaries
  async function refreshSummary(id) {
    const refreshed = await postJSON(`/api/refresh-summary/${id}`, {});
    setSummaries(
      summaries.map((s) => (s.id === id ? { ...s, ...refreshed } : s))
    );
  }

  // PDF Upload
  async function uploadPDF() {
    if (!selectedFile) return;
    const uploaded = await postFile("/api/upload-pdf", selectedFile);
    setSummaries([...summaries, uploaded]);
    setSelectedFile(null);
  }

  // Copilot
  async function runCopilotCommand(command) {
    const result = await postJSON("/api/copilot/process-command", { command });
    setCopilotResponse(result.response);
  }

  return (
    <div className="App">
      <header className="app-header">
        <h1>📚 Resource App</h1>
        <p>Status: {online ? "🟢 Online" : "🔴 Offline"}</p>
      </header>

      {/* Tabs */}
      <nav className="tabs">
        {["pdf", "notes", "schedule", "summaries", "copilot"].map((tab) => (
          <button
            key={tab}
            className={activeTab === tab ? "active" : ""}
            onClick={() => setActiveTab(tab)}
          >
            {tab.toUpperCase()}
          </button>
        ))}
      </nav>

      {/* PDF Upload */}
      {activeTab === "pdf" && (
        <section>
          <h2>Upload PDF</h2>
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => setSelectedFile(e.target.files[0])}
          />
          <button onClick={uploadPDF}>Upload & Summarize</button>
        </section>
      )}

      {/* Notes */}
      {activeTab === "notes" && (
        <section>
          <h2>Notes</h2>
          <input
            placeholder="Title"
            value={noteTitle}
            onChange={(e) => setNoteTitle(e.target.value)}
          />
          <textarea
            placeholder="Content"
            value={noteContent}
            onChange={(e) => setNoteContent(e.target.value)}
          />
          <button onClick={createNote}>Add Note</button>
          <ul>
            {notes.map((note) => (
              <li key={note.id}>
                <strong>{note.title}</strong>: {note.content}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Schedules */}
      {activeTab === "schedule" && (
        <section>
          <h2>Schedules</h2>
          <button onClick={createSchedule}>Create Schedule</button>
          <ul>
            {schedules.map((s) => (
              <li key={s.id}>
                {s.title} — {s.description}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Summaries */}
      {activeTab === "summaries" && (
        <section>
          <h2>Summaries</h2>
          <ul>
            {summaries.map((s) => (
              <li key={s.id}>
                <strong>{s.filename || "Summary"}:</strong> {s.summary}
                <button onClick={() => refreshSummary(s.id)}>Refresh</button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Copilot */}
      {activeTab === "copilot" && (
        <section>
          <h2>Copilot</h2>
          <input
            type="text"
            placeholder="Type a command..."
            onKeyDown={(e) =>
              e.key === "Enter" && runCopilotCommand(e.target.value)
            }
          />
          <p>Response: {copilotResponse}</p>
        </section>
      )}
    </div>
  );
}

export default App;
