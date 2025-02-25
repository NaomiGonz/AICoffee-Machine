import { createBrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import Welcome from "./pages/Welcome.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Home from "./pages/Home.jsx";
import ProtectedRoute from "./tools/ProtectedRoute.jsx";
import Machine from "./pages/Machine.jsx";
import Account from "./pages/Account.jsx";
import CoffeeDetails from "./pages/CoffeeDetails.jsx";

const router = createBrowserRouter([
  {
    path: "/",
    element: <App />, 
    children: [
      {
        index: true, 
        element: <Welcome />,
      },
      {
        path: "login",
        element: <Login />,
      },
      {
        path: "register",
        element: <Register />,
      },
      {
        path: "home",
        element: 
        <ProtectedRoute>
          <Home />
        </ProtectedRoute>,
      },
      {
        path: "machine",
        element: (
          <ProtectedRoute>
            <Machine />
          </ProtectedRoute>
        ),
      },
      {
        path: "account",
        element: (
          <ProtectedRoute>
            <Account />
          </ProtectedRoute>
        ),
      },
      {
        path: "coffee/:coffeeId",
        element: (
          <ProtectedRoute>
            <CoffeeDetails />
          </ProtectedRoute>
        ),
      }
    ],
  },
]);

export default router;
