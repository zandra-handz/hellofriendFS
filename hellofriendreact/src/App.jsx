import react from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import SignIn from './pages/SignIn';
import SignUp from './pages/SignUp';
import SignOut from './pages/SignOut';
import NotFound from './pages/NotFound';
import Home from './pages/Home';
import ProtectedRoute from './components/ProtectedRoute';
import { AuthUserProvider } from './context/AuthUserProvider'; 
import { SelectedFriendProvider } from './context/SelectedFriendProvider'; 
import { FriendListProvider } from './context/FriendListProvider'; 
import { CapsuleListProvider } from './context/CapsuleListProvider'; 
import { FocusModeProvider } from './context/FocusModeProvider'; 
import { ThemeModeProvider } from './context/ThemeModeProvider'; 

function Signout() {
  localStorage.clear()
  return <Navigate to='/signin' />
}

// Need to clear any tokens that might be there 
function SignupandSignout() {
  localStorage.clear()
  return <SignUp />
}


function App() {
	return(
    <BrowserRouter>
      <Routes>
        <Route 
          path='/'
          element={
            <ProtectedRoute>
              <AuthUserProvider>
                <SelectedFriendProvider>
                  <FriendListProvider>
                    <CapsuleListProvider>  
                      <FocusModeProvider>
                        <ThemeModeProvider>
                          <Home />
                        </ThemeModeProvider>
                      </FocusModeProvider>
                    </CapsuleListProvider>
                  </FriendListProvider>
                </SelectedFriendProvider>
              </AuthUserProvider>
            </ProtectedRoute>
          }
        />
        <Route path='/signin' element={<SignIn />}/>
        <Route path='/signout' element={<Signout />}/>
        <Route path='/signup' element={<SignupandSignout />}/>
        <Route path='*' element={<NotFound />}></Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App;
