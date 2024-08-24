import { createBrowserRouter, createRoutesFromElements, Route, RouterProvider } from "react-router-dom";
import RootLayout from "./layout/RootLayout";
import LoginPage from "./pages/LoginPage";
import { ToastContainer } from "react-toastify";
  import "react-toastify/dist/ReactToastify.css";
import VerifyEmailPage from "./pages/VerifyEmailPage";



const router = createBrowserRouter(
    createRoutesFromElements([
        <Route>
            <Route path="/" element={<RootLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />
            </Route>
        </Route>,
    ])
);

const App = () => {
  return (
      <>
          <RouterProvider router={router} />

          <ToastContainer />
      </>
  );
};

export default App;
