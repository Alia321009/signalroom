import { useEffect, useState } from "react";
import { isAuthenticated, onAuthChange } from "./lib/auth";
import { LoginScreen } from "./components/LoginScreen";
import { Dashboard } from "./components/Dashboard";

export default function App() {
  const [authed, setAuthed] = useState(isAuthenticated());

  useEffect(() => onAuthChange(setAuthed), []);

  return authed ? <Dashboard /> : <LoginScreen />;
}
