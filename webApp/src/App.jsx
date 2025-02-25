import React from "react";
import { Outlet } from "react-router-dom";

const App = () => {
  return (
    <div>
      {/* 
        MAYBE: NavBar? 
        Could add more public pages like about the team and mechanical/hardware details
      */}
      <Outlet />
    </div>
  );
};

export default App;

