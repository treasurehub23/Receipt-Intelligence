
import { useState } from "react";
import Login from "./Login";
import Display from "./display";

export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(
    Boolean(localStorage.getItem("access_token"))
  );

  function handleLogout() {
    localStorage.removeItem("access_token");
    setIsLoggedIn(false);
  }

  if (!isLoggedIn) {
    return <Login onLogin={() => setIsLoggedIn(true)} />;
  }

  return (
    <main>
      <button onClick={handleLogout}>Log out</button>
      <Display />
    </main>
  );
}
