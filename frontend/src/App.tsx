import { createBrowserRouter, createRoutesFromElements, Route, RouterProvider } from "react-router-dom";
import RootLayout from "./layout/RootLayout";
import LoginPage from "./pages/LoginPage";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import VerifyEmailPage from "./pages/VerifyEmailPage";
import AuthRequired from "./layout/AuthRequired";
import Protected from "./layout/Protected";
import HomePage from "./pages/HomePage";

const router = createBrowserRouter(
    createRoutesFromElements([
        <Route path="/" element={<RootLayout />}>
            <Route path="/" element={<Protected />}>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/verify-email" element={<VerifyEmailPage />} />
        </Route>
      </Route>,
      <Route path="/" element={<RootLayout />}>
            <Route path="/" element={<AuthRequired />}>
                <Route path="/" element={<HomePage />} />
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
