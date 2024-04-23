import UserCredForm from '../components/UserCredForm.jsx';


function SignIn() {
	return <UserCredForm route='/users/token/' method='signin' />
}


export default SignIn;