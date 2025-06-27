import streamlit as st
import pandas as pd
import numpy as np

# Add a title to the app
st.title("Streamlit Demonstration App")

# Add some text
st.write("This app showcases some of the basic features of Streamlit.")

# Create a simple dataframe
data = {
    'Column 1': np.random.rand(10),
    'Column 2': np.random.rand(10),
    'Column 3': np.random.rand(10)
}
df = pd.DataFrame(data)

# Display the dataframe as a table
st.write("Here is a sample dataframe:")
st.write(df)

# Create a line chart
st.line_chart(df)

# Add a slider widget
st.write("Use the slider to change the value:")
x = st.slider('x', value=50)
st.write(x, 'squared is', x * x)

# Add a button
if st.button('Say hello'):
    st.write('Why hello there')
else:
    st.write('Goodbye')

# Add a selectbox
option = st.selectbox(
    'How would you like to be contacted?',
    ('Email', 'Home phone', 'Mobile phone'))

st.write('You selected:', option)

# Add a checkbox to show/hide data
if st.checkbox('Show raw data'):
    st.subheader('Raw data')
    st.write(df)
